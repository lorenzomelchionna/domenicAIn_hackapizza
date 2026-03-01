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
    def closed_bid(*, bids: list[dict[str, Any]]) -> str:
        """Submit bids to the blind ingredient auction (closed_bid phase only).

        Call this once per turn during closed_bid with ALL ingredients you want to buy.
        The auction is blind: you do not see competitors' bids. Higher bids win.
        Each bid is per-unit; total cost = bid × quantity.

        Args:
            bids: List of bid objects, each with:
                - ingredient (str): exact ingredient name
                - bid (float): price per unit you are willing to pay
                - quantity (int): number of units to buy

        Returns:
            Server response confirming bid submission or describing errors.
        """
        try:
            validated = [AuctionBid(**bid) for bid in bids]
        except ValidationError as e:
            return f"Error: invalid bid format - {e}"
        api_bids = [b.model_dump() for b in validated]
        return client.call("closed_bid", {"bids": api_bids})

    @tool
    def save_menu(*, items: list[dict[str, Any]]) -> str:
        """Publish the restaurant menu to the game server, making it visible to clients.

        Call this during the waiting phase after confirming which recipes you can actually
        prepare with your current inventory. Prices must cover ingredient costs; aim for profit.
        Overwrites any previously published menu.

        Args:
            items: List of menu items, each with:
                - name (str): recipe name — must match EXACTLY a name from get_recipes()
                - price (float): selling price in game currency

        Returns:
            Server response confirming the menu was saved, or an error message.
        """
        try:
            validated = [MenuItem(**item) for item in items]
        except ValidationError as e:
            return f"Error: invalid menu item format - {e}"
        api_items = [m.model_dump() for m in validated]
        return client.call("save_menu", {"items": api_items})

    @tool
    def prepare_dish(dish_name: str, client_id: str) -> str:
        """Start preparing a dish for a client (serving phase only).

        Call this when a client arrives and their order matches a dish on the menu.
        Preparation is asynchronous: you will receive a preparation_complete event when
        the dish is ready. Do NOT call serve_dish before receiving that event.

        Args:
            dish_name (str): Name of the dish to prepare — must match exactly a name on the menu.
            client_id (str): ID of the client who ordered this dish — required to track who to serve.

        Returns:
            Server response confirming preparation started, or an error message.
        """
        result = client.call("prepare_dish", {"dish_name": dish_name})
        if state_getter is not None and "error" not in result.lower():
            state = state_getter()
            state.dishes_in_preparation[dish_name] = client_id
        return result

    @tool
    def serve_dish(dish_name: str, client_id: str) -> str:
        """Deliver a prepared dish to a specific client (serving phase only).

        Only call this after receiving a preparation_complete event for the dish.
        CRITICAL: verify the client has no intolerances that conflict with the dish
        ingredients before calling this — serving an incompatible dish harms reputation.

        Args:
            dish_name (str): Name of the dish that finished preparation.
            client_id (str): ID of the client who ordered it — use get_client_for_dish() to find it.

        Returns:
            Server response confirming delivery, or an error message.
        """
        result = client.call("serve_dish", {"dish_name": dish_name, "client_id": client_id})
        if state_getter is not None and "error" not in result.lower():
            state = state_getter()
            state.dishes_in_preparation.pop(dish_name, None)
        return result

    @tool
    def create_market_entry(side: str, ingredient_name: str, quantity: int, price: float) -> str:
        """Post a BUY or SELL order on the secondary ingredient market.

        Use this to acquire missing ingredients without the auction, or to sell surplus
        stock that will expire at end of turn. Prices are negotiated peer-to-peer.

        Args:
            side (str): 'BUY' to purchase ingredients, 'SELL' to offer them.
            ingredient_name (str): Exact ingredient name.
            quantity (int): Number of units.
            price (float): Price per unit you are offering or requesting.

        Returns:
            Server response with the created entry ID, or an error message.
        """
        return client.call(
            "create_market_entry",
            {"side": side, "ingredient_name": ingredient_name, "quantity": quantity, "price": price},
        )

    @tool
    def execute_transaction(market_entry_id: int) -> str:
        """Accept and execute an existing market entry posted by another restaurant.

        Use this to buy ingredients listed for sale, or to sell ingredients to a buyer.
        Funds and ingredients transfer immediately upon execution.

        Args:
            market_entry_id (int): ID of the market entry to accept.

        Returns:
            Server response confirming the transaction, or an error message.
        """
        return client.call("execute_transaction", {"market_entry_id": market_entry_id})

    @tool
    def delete_market_entry(market_entry_id: int) -> str:
        """Cancel and remove one of your own open market entries.

        Use this if your strategy changes and you no longer want to buy or sell
        the ingredients listed in that entry.

        Args:
            market_entry_id (int): ID of your own market entry to cancel.

        Returns:
            Server response confirming deletion, or an error message.
        """
        return client.call("delete_market_entry", {"market_entry_id": market_entry_id})

    @tool
    def update_restaurant_is_open(is_open: bool) -> str:
        """Open or close the restaurant.

        Call with is_open=True at the start of each turn (speaking phase) so clients
        can place orders. Call with is_open=False to stop accepting new clients.
        During serving phase only closing (is_open=False) is permitted.

        Args:
            is_open (bool): True to open, False to close.

        Returns:
            Server response confirming the new status, or an error message.
        """
        return client.call("update_restaurant_is_open", {"is_open": is_open})

    @tool
    def send_message(recipient_id: int, text: str) -> str:
        """Send a private text message to another restaurant.

        Use this for diplomacy, trade negotiations, or any inter-restaurant communication.

        Args:
            recipient_id (int): The restaurant ID of the recipient.
            text (str): The message body.

        Returns:
            Server response confirming delivery, or an error message.
        """
        return client.call("send_message", {"recipient_id": recipient_id, "text": text})

    @tool
    def get_recipes() -> str:
        """Return the full catalogue of available recipes.

        Call this to see all dishes that can be cooked this turn. Use the returned data
        to select recipes that match the current market strategy (e.g. fast prep, high
        prestige, few ingredients). Each recipe includes name, preparationTimeMs,
        prestige, and ingredients with quantities.

        Returns:
            JSON array of recipe objects:
            [{name, preparationTimeMs, prestige, ingredients: {name: quantity}}, ...]
        """
        if state_getter is None:
            return json.dumps({"error": "state_getter not configured"})
        state = state_getter()
        return json.dumps(state.recipes, ensure_ascii=False)

    @tool
    def get_inventory() -> str:
        """Return the current ingredient inventory.

        Use this to check which ingredients are available and in what quantities.
        Cross-reference with recipe requirements to determine which dishes can actually
        be prepared. Ingredients expire at end of turn — cook them or they are lost.

        Returns:
            JSON object mapping ingredient name to available quantity: {ingredient: quantity, ...}
        """
        if state_getter is None:
            return json.dumps({"error": "state_getter not configured"})
        state = state_getter()
        return json.dumps(state.inventory, ensure_ascii=False)

    @tool
    def save_draft_menu(*, items: list[dict[str, Any]]) -> str:
        """Save the pre-bid recipe selection as a shared draft for downstream agents.

        This is the FINAL action of Menu Decider Pre-Bid. It records the chosen recipes
        so that the Auction Broker knows which ingredients to bid on and the Menu Decider
        Post-Bid can set prices.

        IMPORTANT: this does NOT publish anything to the game server — it only updates
        the shared in-memory state. Call save_menu() later to publish.

        Args:
            items: List of recipe objects, each with:
                - name (str): recipe name
                - ingredients (list): [{name: str, quantity: int}, ...]

        Returns:
            Confirmation string listing the saved recipe names, or an error message.
        """
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
        """Return the draft menu selected by Menu Decider Pre-Bid.

        Use this to retrieve the recipes already chosen for this turn before publishing
        the final menu. The Auction Broker reads this to know which ingredients to bid on.
        The Menu Decider Post-Bid reads this to set dish prices.

        Returns:
            JSON array of recipe objects: [{name, ingredients: [{name, quantity}]}, ...]
            Empty array if no draft has been saved yet.
        """
        if state_getter is None:
            return json.dumps({"error": "state_getter not configured"})
        state = state_getter()
        return json.dumps(state.draft_menu, ensure_ascii=False)

    @tool
    def save_suggested_bids(*, suggested_bids: list[dict[str, Any]]) -> str:
        """Persist the Analyst's recommended bid prices to shared state.

        The Analyst calls this after running market analysis. The Auction Broker will
        later read these values via get_suggested_bids() to decide how much to bid per
        ingredient in the auction.

        Args:
            suggested_bids: List of bid recommendations, each with:
                - ingredient (str): exact ingredient name
                - price (float): recommended bid price per unit

        Returns:
            Confirmation string listing the saved ingredients, or an error message.
        """
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
        """Return the list of clients currently waiting to be served (serving phase).

        Check intolerances for each client before preparing a dish to avoid serving
        incompatible food, which would damage reputation.

        Returns:
            JSON array of client objects: [{id, name, intolerances: [str], ...}, ...]
            Empty array if no clients are waiting.
        """
        if state_getter is None:
            return json.dumps({"error": "state_getter not configured"})
        state = state_getter()
        return json.dumps(state.pending_clients, ensure_ascii=False)

    @tool
    def get_client_for_dish(dish_name: str) -> str:
        """Get the client_id for a dish that was prepared.

        Call this when a dish is ready (preparation_complete event) to find out
        which client ordered it. Returns the client_id that was saved when
        prepare_dish was called.

        Args:
            dish_name (str): Name of the dish that finished preparation.

        Returns:
            The client_id string, or an error message if not found.
        """
        if state_getter is None:
            return json.dumps({"error": "state_getter not configured"})
        state = state_getter()
        client_id = state.dishes_in_preparation.get(dish_name)
        if client_id:
            return client_id
        return json.dumps({"error": f"No client found for dish: {dish_name}"})

    @tool
    def get_suggested_bids() -> str:
        """Return the Analyst's recommended bid prices for this turn.

        Read these before constructing bids in closed_bid(). If the Analyst has run,
        these values are calibrated to market history and should be preferred over
        static guesses. If the list is empty, the Analyst has not yet produced
        recommendations — fall back to a conservative default strategy.

        Returns:
            JSON array: [{ingredient, price}, ...]
            Empty array if no suggestions have been saved this turn.
        """
        if state_getter is None:
            return json.dumps({"error": "state_getter not configured"})
        state = state_getter()
        bids = [
            SuggestedBid(ingredient=ing, price=price).model_dump()
            for ing, price in state.suggested_bids
        ]
        return json.dumps(bids, ensure_ascii=False)

    @tool
    def save_actual_bids(*, actual_bids: list[dict[str, Any]]) -> str:
        """Persist the auction outcome (prices actually paid) to shared state.

        Call this AFTER closed_bid() returns. Parse the server response to extract
        the per-unit price paid for each ingredient and whether the bid was successful.
        This data is later used by calculate_suggested_prices() to estimate dish costs.

        Args:
            actual_bids: List of auction results, each with:
                - ingredient (str): ingredient name
                - price (float): actual price per unit paid
                - success (bool): whether the bid was won

        Returns:
            Confirmation string listing saved ingredients, or an error message.
        """
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
        """Return the auction results from this turn.

        Use this to see which ingredients were acquired, at what price, and whether bids
        were successful. Useful for post-auction analysis and informing future bid strategy.

        Returns:
            JSON array: [{ingredient, price, success}, ...]
            Empty array if no auction results have been recorded yet.
        """
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
        """Compute estimated costs and suggested selling prices for all draft menu recipes.

        This is the PRIMARY tool for Menu Decider Post-Bid. Call it first, then use the
        output to decide which dishes to publish and at what price via save_menu().

        Cost estimation logic:
        - For each ingredient, the price from actual_bids (saved by the Auction Broker)
          is used. If a bid is missing, fallback_cost_per_unit is applied.
        - Estimated cost = sum(ingredient_price × quantity) per recipe.
        - Suggested price = estimated_cost × (1 + markup_percent / 100), rounded.
        - can_make = True only if current inventory covers all ingredient quantities.

        Args:
            markup_percent (float): Profit margin to add on top of cost (default 10%).
            fallback_cost_per_unit (float): Unit cost assumption when no auction data
                is available for an ingredient (default 15.0).

        Returns:
            JSON array: [{name, estimated_cost, suggested_price, can_make}, ...]
            Only includes recipes currently saved in the draft menu.
        """
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
        get_client_for_dish,
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

    
