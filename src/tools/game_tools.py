"""@tool wrappers for Hackapizza MCP tools. Created via factory to inject MCP client."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Callable

from datapizza.tools import tool

if TYPE_CHECKING:
    from .mcp_client import MCPClient


def create_game_tools(mcp_client: MCPClient, state_getter: Callable | None = None) -> tuple[list, dict]:
    """Create tool functions bound to the given MCP client and optional state getter."""
    client = mcp_client

    @tool
    def closed_bid(bids: list[dict[str, Any]]) -> str:
        """Submit bids for the ingredient auction. Only available in closed_bid phase.
        Each bid: {ingredient: str, bid: number, quantity: number}"""
        return client.call("closed_bid", {"bids": bids})

    @tool
    def save_menu(items: list[dict[str, Any]]) -> str:
        """Set or update the restaurant menu. Items: [{name: str, price: number}].
        Names must match valid recipe names. Available in speaking, closed_bid, waiting."""
        return client.call("save_menu", {"items": items})

    @tool
    def prepare_dish(dish_name: str) -> str:
        """Start preparing a dish. Only in serving phase. Wait for preparation_complete before serve_dish."""
        return client.call("prepare_dish", {"dish_name": dish_name})

    @tool
    def serve_dish(dish_name: str, client_id: str) -> str:
        """Serve a prepared dish to a client. Only in serving. Check intolerances first!"""
        return client.call("serve_dish", {"dish_name": dish_name, "client_id": client_id})

    @tool
    def create_market_entry(side: str, ingredient_name: str, quantity: int, price: float) -> str:
        """Create a BUY or SELL market entry. side: 'BUY' or 'SELL'."""
        return client.call(
            "create_market_entry",
            {"side": side, "ingredient_name": ingredient_name, "quantity": quantity, "price": price},
        )

    @tool
    def execute_transaction(market_entry_id: int) -> str:
        """Accept an existing market entry (buy or sell)."""
        return client.call("execute_transaction", {"market_entry_id": market_entry_id})

    @tool
    def delete_market_entry(market_entry_id: int) -> str:
        """Remove your own market entry."""
        return client.call("delete_market_entry", {"market_entry_id": market_entry_id})

    @tool
    def update_restaurant_is_open(is_open: bool) -> str:
        """Open or close the restaurant. In serving phase, only close (is_open=false) is allowed."""
        return client.call("update_restaurant_is_open", {"is_open": is_open})

    @tool
    def send_message(recipient_id: int, text: str) -> str:
        """Send a direct message to another restaurant (team). recipient_id is the restaurant id."""
        return client.call("send_message", {"recipient_id": recipient_id, "text": text})

    @tool
    def get_recipes() -> str:
        """Get all available recipes. Returns a JSON list of recipes with name, ingredients, prep_time, and prestige.
        ALWAYS call this tool first to know which dishes you can add to the menu."""
        if state_getter is None:
            return json.dumps({"error": "state_getter not configured"})
        state = state_getter()
        return json.dumps(state.recipes, ensure_ascii=False)

    @tool
    def get_inventory() -> str:
        """Get current ingredient inventory. Returns a JSON dict of ingredient -> quantity."""
        if state_getter is None:
            return json.dumps({"error": "state_getter not configured"})
        state = state_getter()
        return json.dumps(state.inventory, ensure_ascii=False)

    @tool
    def save_draft_menu(items: list[dict[str, Any]]) -> str:
        """Save the draft menu (selected recipes for this turn) to shared state.
        Items is a list of recipe objects: [{name: str, ingredients: [{name: str, quantity: int}]}].
        This does NOT publish the menu to the game server — it only saves the draft locally."""
        if state_getter is None:
            return "Error: state_getter not configured"
        if not isinstance(items, list):
            return "Error: items must be a list"
        state = state_getter()
        state.draft_menu = items
        return f"Draft menu saved with {len(items)} recipes: {[r.get('name', '?') for r in items]}"

    @tool
    def get_draft_menu() -> str:
        """Get the current draft menu from shared state. Returns a JSON list of selected recipes
        with their ingredients. Use this to know which dishes were chosen by the Menu Decider Pre-Bid."""
        if state_getter is None:
            return json.dumps({"error": "state_getter not configured"})
        state = state_getter()
        return json.dumps(state.draft_menu, ensure_ascii=False)

    @tool
    def save_suggested_bids(suggested_bids: list[dict[str, Any]]) -> str:
        """Save analyst output: suggested bid per unit for each ingredient.
        Input: [{\"ingredient\": str, \"price\": float}, ...].
        The analyst calls this after analyzing the market. The broker will use these for bidding."""
        if state_getter is None:
            return "Error: state_getter not configured"
        if not isinstance(suggested_bids, list):
            return "Error: suggested_bids must be a list"
        state = state_getter()
        parsed: list[tuple[str, float]] = []
        for item in suggested_bids:
            if isinstance(item, dict):
                ing = item.get("ingredient")
                price = item.get("price")
                if ing is not None and price is not None:
                    parsed.append((str(ing), float(price)))
        state.suggested_bids = parsed
        return f"Suggested bids saved for {len(parsed)} ingredients: {[p[0] for p in parsed]}"

    @tool
    def get_suggested_bids() -> str:
        """Get analyst suggested bids: [(ingredient, price_per_unit), ...].
        Use these as bidding prices when available. If empty, fall back to static strategy."""
        if state_getter is None:
            return json.dumps({"error": "state_getter not configured"})
        state = state_getter()
        # Return as list of dicts for JSON
        data = [{"ingredient": ing, "price": price} for ing, price in state.suggested_bids]
        return json.dumps(data, ensure_ascii=False)

    @tool
    def save_actual_bids(actual_bids: list[dict[str, Any]]) -> str:
        """Save auction results: actual prices and success status per ingredient.
        Input: [{\"ingredient\": str, \"price\": float, \"success\": bool}, ...].
        Call this AFTER closed_bid. Parse the closed_bid response: price = actual paid per unit, success = whether purchase went through."""
        if state_getter is None:
            return "Error: state_getter not configured"
        if not isinstance(actual_bids, list):
            return "Error: actual_bids must be a list"
        state = state_getter()
        parsed: list[dict[str, Any]] = []
        for item in actual_bids:
            if isinstance(item, dict):
                ing = item.get("ingredient")
                price = item.get("price")
                success = item.get("success")
                if ing is not None:
                    parsed.append({
                        "ingredient": str(ing),
                        "price": float(price) if price is not None else 0.0,
                        "success": bool(success) if success is not None else False,
                    })
        state.actual_bids = parsed
        return f"Actual bids saved for {len(parsed)} ingredients: {[p['ingredient'] for p in parsed]}"

    @tool
    def get_actual_bids() -> str:
        """Get auction results: [{ingredient, price, success}, ...]. Use for analytics or learning."""
        if state_getter is None:
            return json.dumps({"error": "state_getter not configured"})
        state = state_getter()
        return json.dumps(state.actual_bids, ensure_ascii=False)

    all_tools = [
        closed_bid,
        save_menu,
        prepare_dish,
        serve_dish,
        create_market_entry,
        execute_transaction,
        delete_market_entry,
        update_restaurant_is_open,
        send_message,
        get_recipes,
        get_inventory,
        save_draft_menu,
        get_draft_menu,
        save_suggested_bids,
        get_suggested_bids,
        save_actual_bids,
        get_actual_bids,
    ]
    by_name = {t.__name__: t for t in all_tools}
    return all_tools, by_name

