"""@tool wrappers for Hackapizza MCP tools. Created via factory to inject MCP client."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Callable

from datapizza.tools import tool
from pydantic import ValidationError

from src.schemas import Recipe, MenuItem, SuggestedBid, AuctionBid, ActualBid

if TYPE_CHECKING:
    from .mcp_client import MCPClient


def create_game_tools(mcp_client: MCPClient, state_getter: Callable | None = None) -> tuple[list, dict]:
    """Create tool functions bound to the given MCP client and optional state getter."""
    client = mcp_client

    @tool
    def closed_bid(bids: list[dict[str, Any]]) -> str:
        """Submit bids for the ingredient auction. Only available in closed_bid phase.
        Each bid: {ingredient: str, bid: number, quantity: number}"""
        try:
            validated = [AuctionBid(**bid) for bid in bids]
        except ValidationError as e:
            return f"Error: invalid bid format - {e}"
        api_bids = [b.model_dump() for b in validated]
        return client.call("closed_bid", {"bids": api_bids})

    @tool
    def save_menu(items: list[dict[str, Any]]) -> str:
        """Set or update the restaurant menu. Items: [{name: str, price: number}].
        Names must match valid recipe names. Available in speaking, closed_bid, waiting."""
        try:
            validated = [MenuItem(**item) for item in items]
        except ValidationError as e:
            return f"Error: invalid menu item format - {e}"
        api_items = [m.model_dump() for m in validated]
        return client.call("save_menu", {"items": api_items})

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
        """Get ALL available recipes. Returns a JSON list of recipes with name, ingredients,
        preparationTimeMs, and prestige. Use this to browse the full catalogue."""
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
        try:
            validated = [Recipe(**item) for item in items]
        except ValidationError as e:
            return f"Error: invalid recipe format - {e}"
        state = state_getter()
        state.draft_menu = [r.model_dump() for r in validated]
        return f"Draft menu saved with {len(validated)} recipes: {[r.name for r in validated]}"

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
        try:
            validated = [SuggestedBid(**bid) for bid in suggested_bids]
        except ValidationError as e:
            return f"Error: invalid bid format - {e}"
        state = state_getter()
        state.suggested_bids = [(b.ingredient, b.price) for b in validated]
        return f"Suggested bids saved for {len(validated)} ingredients: {[b.ingredient for b in validated]}"


    @tool
    def get_pending_clients() -> str:
        """Get the list of pending clients waiting to be served. Returns a JSON list of clients with id, name, and intolerances."""
        if state_getter is None:
            return json.dumps({"error": "state_getter not configured"})
        state = state_getter()
        return json.dumps(state.pending_clients, ensure_ascii=False)

    @tool
    def get_suggested_bids() -> str:
        """Get analyst suggested bids: [(ingredient, price_per_unit), ...].
        Use these as bidding prices when available. If empty, fall back to static strategy."""
        if state_getter is None:
            return json.dumps({"error": "state_getter not configured"})
        state = state_getter()
        bids = [
            SuggestedBid(ingredient=ing, price=price).model_dump()
            for ing, price in state.suggested_bids
        ]
        return json.dumps(bids, ensure_ascii=False)

    @tool
    def save_actual_bids(actual_bids: list[dict[str, Any]]) -> str:
        """Save auction results: actual prices and success status per ingredient.
        Input: [{\"ingredient\": str, \"price\": float, \"success\": bool}, ...].
        Call this AFTER closed_bid. Parse the closed_bid response: price = actual paid per unit, success = whether purchase went through."""
        if state_getter is None:
            return "Error: state_getter not configured"
        try:
            validated = [ActualBid(**bid) for bid in actual_bids]
        except ValidationError as e:
            return f"Error: invalid bid result format - {e}"
        state = state_getter()
        state.actual_bids = [b.model_dump() for b in validated]
        return f"Actual bids saved for {len(validated)} ingredients: {[b.ingredient for b in validated]}"

    @tool
    def get_actual_bids() -> str:
        """Get auction results: [{ingredient, price, success}, ...]. Use for analytics or learning."""
        if state_getter is None:
            return json.dumps({"error": "state_getter not configured"})
        state = state_getter()
        bids = [ActualBid(**bid).model_dump() for bid in state.actual_bids]
        return json.dumps(bids, ensure_ascii=False)

    @tool
    def calculate_suggested_prices(
        markup_percent: float = 10.0,
        fallback_cost_per_unit: float = 15.0,
    ) -> str:
        """Calculate cost and suggested selling price for each recipe in the draft menu.
        Uses actual_bids for ingredient prices when available, else fallback_cost_per_unit.
        Applies markup_percent above cost. Also checks if we have enough inventory to make each dish.
        Returns JSON: [{name, estimated_cost, suggested_price, can_make}, ...].
        Use this to set profitable prices before calling save_menu."""
        if state_getter is None:
            return json.dumps({"error": "state_getter not configured"})
        state = state_getter()

        price_map: dict[str, float] = {}
        for bid in state.actual_bids:
            if isinstance(bid, dict) and bid.get("ingredient"):
                price_map[str(bid["ingredient"])] = float(bid.get("price", 0) or 0)

        def _price_for(ingredient: str) -> float:
            return price_map.get(ingredient, fallback_cost_per_unit)

        def _ingredients_from_recipe(recipe: dict) -> list[tuple[str, int]]:
            ing = recipe.get("ingredients")
            if isinstance(ing, list):
                return [(it.get("name", ""), int(it.get("quantity", 0))) for it in ing if it.get("name")]
            if isinstance(ing, dict):
                return [(k, int(v)) for k, v in ing.items()]
            return []

        result = []
        for item in state.draft_menu:
            name = item.get("name", "")
            if not name:
                continue
            pairs = _ingredients_from_recipe(item)
            cost = sum(qty * _price_for(ing) for ing, qty in pairs)
            suggested = round(cost * (1 + markup_percent / 100))
            can_make = all(state.inventory.get(ing, 0) >= qty for ing, qty in pairs)
            result.append({
                "name": name,
                "estimated_cost": round(cost, 2),
                "suggested_price": suggested,
                "can_make": can_make,
            })

        return json.dumps(result, ensure_ascii=False)

    all_tools = [
        closed_bid,
        save_menu,
        prepare_dish,
        serve_dish,
        create_market_entry,
        execute_transaction,
        delete_market_entry,
        update_restaurant_is_open,
        get_pending_clients,
        send_message,
        get_recipes,
        get_inventory,
        save_draft_menu,
        get_draft_menu,
        save_suggested_bids,
        get_suggested_bids,
        save_actual_bids,
        get_actual_bids,
        calculate_suggested_prices,
    ]
    by_name = {t.__name__: t for t in all_tools}
    return all_tools, by_name

    
