"""@tool wrappers for Hackapizza MCP tools. Created via factory to inject MCP client."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from datapizza.tools import tool

if TYPE_CHECKING:
    from .mcp_client import MCPClient


def create_game_tools(mcp_client: MCPClient) -> list:
    """Create tool functions bound to the given MCP client."""
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
    ]
    by_name = {t.__name__: t for t in all_tools}
    return all_tools, by_name
