"""Hackapizza 2.0 multi-agent restaurant - main entry point."""
import asyncio
from datetime import datetime
from typing import Any

from datapizza.clients.openai_like import OpenAILikeClient

from src.config import BASE_URL, DB_PATH, REGOLO_API_KEY, REGOLO_BASE_URL, REGOLO_MODEL, TEAM_API_KEY, TEAM_ID, validate_config
from src.logging_config import setup_loggers
from src.monitor_state import write_monitor_state
from src.state import GameState, StateUpdater
from src.sse import listen, log
from src.tools import MCPClient
from src.agents import create_all_agents
from src.data_collector import DataCollector


async def main() -> None:
    setup_loggers()
    validate_config()

    state = GameState(restaurant_id=TEAM_ID)
    state_updater = StateUpdater(BASE_URL, TEAM_API_KEY, TEAM_ID)
    data_collector = DataCollector(BASE_URL, TEAM_API_KEY, DB_PATH, TEAM_ID)

    def phase_getter() -> str:
        return state.phase

    mcp_client = MCPClient(BASE_URL, TEAM_API_KEY, phase_getter)

    client = OpenAILikeClient(
        api_key=REGOLO_API_KEY,
        model=REGOLO_MODEL,
        base_url=REGOLO_BASE_URL,
    )

    def state_getter():
        return state

    restaurant_manager, sub_agents = create_all_agents(client, mcp_client, phase_getter, state_getter)
    maitre_agent = next(a for a in sub_agents if a.name == "maitre")

    event_queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()
    event_log: list[dict[str, Any]] = []

    def append_event(tag: str, message: str, data: dict[str, Any] | None = None) -> None:
        event_log.append({
            "tag": tag,
            "message": message,
            "ts": datetime.now().isoformat(),
            **(data or {}),
        })

    async def state_writer_task() -> None:
        """Periodically refresh state from API and write to file for Streamlit dashboard."""
        while True:
            await asyncio.sleep(2)
            try:
                state_updater.refresh_restaurant(state)
                write_monitor_state(state, event_log)
            except Exception as e:
                log("MONITOR", f"write failed: {e}")

    def run_turn_start() -> None:
        """Called on game_started (= speaking phase). Open restaurant, refresh state, run pre-bid."""
        # 1. Open restaurant (hardcoded, no LLM dependency)
        try:
            result = mcp_client.call("update_restaurant_is_open", {"is_open": True})
            log("AGENT", f"restaurant opened: {result}")
        except Exception as e:
            log("ERROR", f"failed to open restaurant: {e}")
        # 2. Refresh state for the new turn
        state_updater.refresh_restaurant(state)
        state_updater.refresh_restaurants(state)
        # 3. Collect initial data for the turn
        try:
            data_collector.collect_restaurants(state.turn_id)
            data_collector.collect_own_restaurant(state.turn_id)
            log("DATA", f"collected initial data for turn {state.turn_id}")
        except Exception as e:
            log("ERROR", f"data collection failed: {e}")
        # 4. Run orchestrator for speaking/pre-bid
        ctx = state.summary()
        msg = f"Current phase: speaking. Execute phase-specific tasks.\n\nContext:\n{ctx}"
        try:
            resp = restaurant_manager.run(msg)
            log("AGENT", f"orchestrator response (speaking): {resp.text[:200] if resp and resp.text else 'ok'}")
            append_event("AGENT", "orchestrator phase=speaking", {"response_preview": (resp.text[:150] if resp and resp.text else "ok")})
        except Exception as e:
            log("ERROR", f"orchestrator failed (speaking): {e}")
            append_event("ERROR", f"orchestrator failed (speaking): {e}")

    def run_orchestrator_for_phase(phase: str) -> None:
        """Called on phase changes (closed_bid, waiting, serving). NOT for speaking — that's in run_turn_start."""
        state_updater.refresh_restaurant(state)
        if phase in ("waiting", "closed_bid"):
            state_updater.refresh_meals(state)
        
        # Collect phase-specific data
        try:
            if phase == "waiting":
                data_collector.collect_bid_history(state.turn_id)
                data_collector.collect_meals(state.turn_id, TEAM_ID)
                log("DATA", f"collected bid_history and meals for turn {state.turn_id}")
            elif phase == "serving":
                data_collector.collect_market_entries(state.turn_id)
                data_collector.collect_restaurants(state.turn_id)
                log("DATA", f"collected market_entries and restaurant menus for turn {state.turn_id}")
            elif phase == "stopped":
                data_collector.collect_all_for_turn(state.turn_id)
                log("DATA", f"collected all end-of-turn data for turn {state.turn_id}")
        except Exception as e:
            log("ERROR", f"data collection failed for phase {phase}: {e}")
        
        ctx = state.summary()
        msg = f"Current phase: {phase}. Execute phase-specific tasks.\n\nContext:\n{ctx}"
        try:
            resp = restaurant_manager.run(msg)
            log("AGENT", f"orchestrator response: {resp.text[:200] if resp and resp.text else 'ok'}")
            append_event("AGENT", f"orchestrator phase={phase}", {"response_preview": (resp.text[:150] if resp and resp.text else "ok")})
        except Exception as e:
            log("ERROR", f"orchestrator failed: {e}")
            append_event("ERROR", f"orchestrator failed: {e}")

    def run_maitre_for_client(data: dict[str, Any]) -> None:
        state_updater.refresh_restaurant(state)  # refresh inventory
        state_updater.refresh_meals(state)
        state_updater.sync_pending_clients(state)
        ctx = state.summary()
        client_name = data.get("clientName", "")
        order_text = data.get("orderText", "")
        intolerances = data.get("intolerances", [])
        msg = (
            f"A new client arrived: {client_name}.\n"
            f"Order: {order_text}\n"
            f"Intolerances: {intolerances}\n\n"
            f"Context:\n{ctx}\n\n"
            f"Match the order to a menu item. Check intolerances. If valid, call prepare_dish."
        )
        try:
            maitre_agent.run(msg)
        except Exception as e:
            log("ERROR", f"maitre (client) failed: {e}")

    def run_maitre_for_serve(data: dict[str, Any]) -> None:
        dish = data.get("dish", "")
        state_updater.refresh_meals(state)
        state_updater.sync_pending_clients(state)
        ctx = state.summary()
        msg = (
            f"Dish ready: {dish}.\n\n"
            f"Context:\n{ctx}\n\n"
            f"Find the client_id from the Pending clients list and call serve_dish(dish_name, client_id)."
        )
        try:
            maitre_agent.run(msg)
        except Exception as e:
            log("ERROR", f"maitre (serve) failed: {e}")

    async def process_events() -> None:
        while True:
            event_type, event_data = await event_queue.get()
            # Log all SSE events to database
            try:
                data_collector.log_sse_event(state.turn_id if state.turn_id > 0 else None, event_type, event_data)
            except Exception as e:
                log("ERROR", f"failed to log SSE event: {e}")
            
            if event_type == "game_started":
                state.turn_id = event_data.get("turn_id", 0)
                state.phase = "speaking"
                state_updater.refresh_recipes(state)
                log("EVENT", f"game started turn_id={state.turn_id}")
                append_event("EVENT", "game_started", {"turn_id": state.turn_id})
                # speaking phase work happens here (open restaurant + pre-bid)
                await asyncio.get_event_loop().run_in_executor(None, run_turn_start)
            elif event_type == "game_phase_changed":
                phase = event_data.get("phase", "unknown")
                state.phase = phase
                log("EVENT", f"phase -> {phase}")
                append_event("EVENT", f"phase -> {phase}", {"phase": phase})
                if phase not in ("stopped", "speaking"):
                    # speaking is handled in game_started above
                    await asyncio.get_event_loop().run_in_executor(None, run_orchestrator_for_phase, phase)
                elif phase == "stopped":
                    # Collect final data when turn ends
                    await asyncio.get_event_loop().run_in_executor(None, run_orchestrator_for_phase, phase)
            elif event_type == "client_spawned":
                log("EVENT", f"client={event_data.get('clientName')} order={event_data.get('orderText')}")
                append_event("EVENT", f"client={event_data.get('clientName')} order={event_data.get('orderText')}", event_data)
                await asyncio.get_event_loop().run_in_executor(None, run_maitre_for_client, event_data)
            elif event_type == "preparation_complete":
                log("EVENT", f"dish ready: {event_data.get('dish')}")
                append_event("EVENT", f"dish ready: {event_data.get('dish')}", event_data)
                await asyncio.get_event_loop().run_in_executor(None, run_maitre_for_serve, event_data)
            elif event_type == "game_reset":
                log("EVENT", "game reset")
                append_event("EVENT", "game reset")
            elif event_type == "message":
                log("EVENT", f"message from {event_data.get('sender')}")
                append_event("EVENT", f"message from {event_data.get('sender')}", event_data)
            elif event_type == "new_message":
                log("EVENT", f"new_message received")
                append_event("EVENT", "new_message received", event_data)

    async def dispatch(event_type: str, event_data: dict[str, Any]) -> None:
        await event_queue.put((event_type, event_data))

    log("INIT", f"team={TEAM_ID} base_url={BASE_URL}")
    state_updater.refresh_recipes(state)
    append_event("INIT", f"team={TEAM_ID} base_url={BASE_URL}")

    processor = asyncio.create_task(process_events())
    writer = asyncio.create_task(state_writer_task())
    try:
        await listen(BASE_URL, TEAM_API_KEY, TEAM_ID, dispatch)
    finally:
        processor.cancel()
        writer.cancel()
        try:
            await processor
        except asyncio.CancelledError:
            pass
        try:
            await writer
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("INIT", "client stopped")
