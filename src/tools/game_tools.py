"""@tool wrappers for Hackapizza MCP tools. Created via factory to inject MCP client."""
from __future__ import annotations

import json
import random
from typing import TYPE_CHECKING, Any, Callable

from datapizza.tools import tool

if TYPE_CHECKING:
    from .mcp_client import MCPClient

# Max bid per ingredient (initial test; TODO: parametrizzare)
MAX_BID_PER_INGREDIENT = 100


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
    def recipes_to_bids(recipe_quantities: list[dict[str, Any]]) -> str:
        """Convert (recipe_name, quantity) list to auction bids. Input: [{"recipe_name": str, "quantity": int}, ...].
        Aggregates ingredients across recipes, assigns random bid per ingredient (max 100).
        Returns JSON list of {ingredient, bid, quantity} for closed_bid."""
        if state_getter is None:
            return json.dumps({"error": "state_getter not configured"})
        recipes = {r["name"]: r for r in state_getter().recipes}
        agg: dict[str, int] = {}
        for item in recipe_quantities:
            name = item.get("recipe_name", "")
            qty = int(item.get("quantity", 0))
            if name not in recipes or qty <= 0:
                continue
            for ing, ing_qty in recipes[name].get("ingredients", {}).items():
                agg[ing] = agg.get(ing, 0) + ing_qty * qty
        bids = [
            {
                "ingredient": ing,
                "quantity": qty,
                "bid": random.randint(1, MAX_BID_PER_INGREDIENT),
            }
            for ing, qty in agg.items()
        ]
        return json.dumps(bids, ensure_ascii=False)

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
        recipes_to_bids,
    ]
    by_name = {t.__name__: t for t in all_tools}
    return all_tools, by_name
