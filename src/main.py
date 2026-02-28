"""Hackapizza 2.0 multi-agent restaurant - main entry point."""
import asyncio
from typing import Any

from datapizza.clients.openai_like import OpenAILikeClient

from src.config import BASE_URL, REGOLO_API_KEY, REGOLO_BASE_URL, REGOLO_MODEL, TEAM_API_KEY, TEAM_ID, validate_config
from src.state import GameState, StateUpdater
from src.sse import listen, log
from src.tools import MCPClient
from src.agents import create_all_agents


async def main() -> None:
    validate_config()

    state = GameState(restaurant_id=TEAM_ID)
    state_updater = StateUpdater(BASE_URL, TEAM_API_KEY, TEAM_ID)

    def phase_getter() -> str:
        return state.phase

    mcp_client = MCPClient(BASE_URL, TEAM_API_KEY, phase_getter)

    client = OpenAILikeClient(
        api_key=REGOLO_API_KEY,
        model=REGOLO_MODEL,
        base_url=REGOLO_BASE_URL,
    )

    restaurant_manager, sub_agents = create_all_agents(client, mcp_client, phase_getter)
    maitre_agent = next(a for a in sub_agents if a.name == "maitre")

    event_queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()

    def run_orchestrator_for_phase(phase: str) -> None:
        state_updater.refresh_restaurant(state)
        if phase in ("waiting", "closed_bid"):
            state_updater.refresh_meals(state)
        if phase != "stopped":
            state_updater.refresh_market(state)
        if phase == "speaking":
            state_updater.refresh_restaurants(state)
        ctx = state.summary()
        msg = f"Current phase: {phase}. Execute phase-specific tasks.\n\nContext:\n{ctx}"
        try:
            resp = restaurant_manager.run(msg)
            log("AGENT", f"orchestrator response: {resp.text[:200] if resp and resp.text else 'ok'}")
        except Exception as e:
            log("ERROR", f"orchestrator failed: {e}")

    def run_maitre_for_client(data: dict[str, Any]) -> None:
        state_updater.refresh_meals(state)
        state_updater.sync_pending_clients(state)
        ctx = state.summary()
        client_name = data.get("clientName", "")
        order_text = data.get("orderText", "")
        msg = f"A new client arrived: {client_name}. Order: {order_text}\n\nContext:\n{ctx}\n\nMatch to menu, check intolerances, call prepare_dish."
        try:
            maitre_agent.run(msg)
        except Exception as e:
            log("ERROR", f"maitre (client) failed: {e}")

    def run_maitre_for_serve(data: dict[str, Any]) -> None:
        dish = data.get("dish", "")
        state_updater.refresh_meals(state)
        state_updater.sync_pending_clients(state)
        ctx = state.summary()
        msg = f"Dish ready: {dish}. Call serve_dish with the correct client_id.\n\nContext:\n{ctx}"
        try:
            maitre_agent.run(msg)
        except Exception as e:
            log("ERROR", f"maitre (serve) failed: {e}")

    async def process_events() -> None:
        while True:
            event_type, event_data = await event_queue.get()
            if event_type == "game_started":
                state.turn_id = event_data.get("turn_id", 0)
                state_updater.refresh_recipes(state)
                log("EVENT", f"game started turn_id={state.turn_id}")
            elif event_type == "game_phase_changed":
                phase = event_data.get("phase", "unknown")
                state.phase = phase
                log("EVENT", f"phase -> {phase}")
                if phase != "stopped":
                    await asyncio.get_event_loop().run_in_executor(None, run_orchestrator_for_phase, phase)
            elif event_type == "client_spawned":
                log("EVENT", f"client={event_data.get('clientName')} order={event_data.get('orderText')}")
                await asyncio.get_event_loop().run_in_executor(None, run_maitre_for_client, event_data)
            elif event_type == "preparation_complete":
                log("EVENT", f"dish ready: {event_data.get('dish')}")
                await asyncio.get_event_loop().run_in_executor(None, run_maitre_for_serve, event_data)
            elif event_type == "game_reset":
                log("EVENT", "game reset")
            elif event_type == "message":
                log("EVENT", f"message from {event_data.get('sender')}")
            elif event_type == "new_message":
                log("EVENT", f"new_message received")

    async def dispatch(event_type: str, event_data: dict[str, Any]) -> None:
        await event_queue.put((event_type, event_data))

    log("INIT", f"team={TEAM_ID} base_url={BASE_URL}")
    state_updater.refresh_recipes(state)

    processor = asyncio.create_task(process_events())
    try:
        await listen(BASE_URL, TEAM_API_KEY, TEAM_ID, dispatch)
    finally:
        processor.cancel()
        try:
            await processor
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("INIT", "client stopped")
