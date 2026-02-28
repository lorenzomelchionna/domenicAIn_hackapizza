"""HTTP client for Hackapizza game server MCP (POST /mcp with JSON-RPC)."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Callable

import requests

from src.logging_config import get_mcp_logger, log_mcp_input, log_mcp_output

if TYPE_CHECKING:
    from src.data import DataCollector

# Phase-to-tool allowlist (tools allowed per phase)
TOOL_PHASES: dict[str, list[str]] = {
    "save_menu": ["speaking", "closed_bid", "waiting"],
    "closed_bid": ["closed_bid"],
    "prepare_dish": ["serving"],
    "serve_dish": ["serving"],
    "create_market_entry": ["speaking", "closed_bid", "waiting", "serving"],
    "execute_transaction": ["speaking", "closed_bid", "waiting", "serving"],
    "delete_market_entry": ["speaking", "closed_bid", "waiting", "serving"],
    "send_message": ["speaking", "closed_bid", "waiting", "serving"],
    "update_restaurant_is_open": ["speaking", "closed_bid", "waiting", "serving"],
}


class MCPClient:
    """Sync client for game server MCP tools."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        phase_getter: Callable[[], str],
        turn_getter: Callable[[], int] | None = None,
        data_collector: DataCollector | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._phase_getter = phase_getter
        self._turn_getter = turn_getter
        self._data_collector = data_collector
        self._request_id = 0
        self._pending_bids: list[dict[str, Any]] = []

    def _get_phase(self) -> str:
        return self._phase_getter()

    def _get_turn(self) -> int:
        return self._turn_getter() if self._turn_getter else 0

    def _call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        mcp_logger = get_mcp_logger()
        log_mcp_input(mcp_logger, name, arguments)

        phase = self._get_phase()
        allowed = TOOL_PHASES.get(name, [])
        if allowed and phase not in allowed:
            out = {
                "isError": True,
                "content": [{"type": "text", "text": f"Tool {name} not allowed in phase {phase}. Allowed phases: {allowed}"}],
            }
            log_mcp_output(mcp_logger, name, out["content"][0]["text"], is_error=True)
            return out

        # update_restaurant_is_open: in serving, only close (is_open=false) allowed
        if name == "update_restaurant_is_open" and phase == "serving":
            if arguments.get("is_open", True):
                out = {
                    "isError": True,
                    "content": [{"type": "text", "text": "In serving phase, can only close (is_open=false), not reopen."}],
                }
                log_mcp_output(mcp_logger, name, out["content"][0]["text"], is_error=True)
                return out

        url = f"{self.base_url}/mcp"
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream, */*",
        }
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
            "id": self._request_id,
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            out = {
                "isError": True,
                "content": [{"type": "text", "text": f"MCP request failed: {e}"}],
            }
            log_mcp_output(mcp_logger, name, str(e), is_error=True)
            return out

        if "error" in data:
            out = {
                "isError": True,
                "content": [{"type": "text", "text": str(data["error"])}],
            }
            log_mcp_output(mcp_logger, name, str(data["error"]), is_error=True)
            return out

        result = data.get("result", {})
        if isinstance(result, dict) and result.get("isError"):
            text = ""
            for c in result.get("content", []):
                if c.get("type") == "text":
                    text += c.get("text", "")
            err_out = {"isError": True, "content": [{"type": "text", "text": text or "Unknown error"}]}
            log_mcp_output(mcp_logger, name, text or "Unknown error", is_error=True)
            return err_out

        out = result if isinstance(result, dict) else {"content": [{"type": "text", "text": str(result)}]}
        result_str = "\n".join(c.get("text", "") for c in out.get("content", []) if c.get("type") == "text") or "OK"
        log_mcp_output(mcp_logger, name, result_str, is_error=False)

        # Data collection hooks
        self._collect_data(name, arguments, out, result_str)

        return out

    def _collect_data(self, name: str, arguments: dict[str, Any], out: dict[str, Any], result_str: str) -> None:
        """Collect data for analytics based on tool calls and results."""
        if not self._data_collector:
            return

        turn_id = self._get_turn()
        if turn_id <= 0:
            return

        try:
            if name == "closed_bid":
                self._collect_bid_data(turn_id, arguments, result_str)
            elif name == "save_menu":
                self._collect_menu_data(turn_id, arguments)
            elif name == "create_market_entry":
                self._collect_market_entry_data(turn_id, arguments, result_str)
            elif name == "execute_transaction":
                self._collect_transaction_data(turn_id, arguments, result_str)
            elif name == "serve_dish":
                self._collect_serve_data(turn_id, arguments, result_str)
        except Exception:
            pass

    def _collect_bid_data(self, turn_id: int, arguments: dict[str, Any], result_str: str) -> None:
        """Collect bid submission and results."""
        if not self._data_collector:
            return

        bids = arguments.get("bids", [])
        for bid in bids:
            self._data_collector.record_bid(
                turn_id=turn_id,
                ingredient=bid.get("ingredient", ""),
                bid_price=bid.get("bid", 0),
                quantity=bid.get("quantity", 0),
            )
            self._pending_bids.append(bid)

        # Try to parse auction results from response
        try:
            if "won" in result_str.lower() or "lost" in result_str.lower():
                self._parse_bid_results(turn_id, result_str)
        except Exception:
            pass

    def _parse_bid_results(self, turn_id: int, result_str: str) -> None:
        """Parse bid results from server response."""
        if not self._data_collector:
            return

        try:
            result_data = json.loads(result_str)
            if isinstance(result_data, list):
                for item in result_data:
                    ingredient = item.get("ingredient", "")
                    won = item.get("won", False)
                    winning_price = item.get("winning_price") or item.get("price")
                    quantity_won = item.get("quantity_won") or item.get("quantity")
                    self._data_collector.update_bid_result(
                        turn_id=turn_id,
                        ingredient=ingredient,
                        won=won,
                        winning_price=winning_price,
                        quantity_won=quantity_won if won else 0,
                    )
        except (json.JSONDecodeError, TypeError):
            pass

    def _collect_menu_data(self, turn_id: int, arguments: dict[str, Any]) -> None:
        """Collect menu items when saved."""
        if not self._data_collector:
            return

        items = arguments.get("items", [])
        self._data_collector.record_menu(turn_id, items)

    def _collect_market_entry_data(self, turn_id: int, arguments: dict[str, Any], result_str: str) -> None:
        """Collect market entry creation."""
        if not self._data_collector:
            return

        entry_id = None
        try:
            result_data = json.loads(result_str)
            if isinstance(result_data, dict):
                entry_id = result_data.get("id") or result_data.get("entry_id")
        except (json.JSONDecodeError, TypeError):
            pass

        self._data_collector.record_market_entry(
            turn_id=turn_id,
            entry_id=entry_id,
            side=arguments.get("side", ""),
            ingredient=arguments.get("ingredient_name", ""),
            quantity=arguments.get("quantity", 0),
            price=arguments.get("price", 0),
            our_entry=True,
        )

    def _collect_transaction_data(self, turn_id: int, arguments: dict[str, Any], result_str: str) -> None:
        """Collect transaction execution."""
        if not self._data_collector:
            return

        entry_id = arguments.get("market_entry_id")
        if entry_id:
            self._data_collector.mark_market_entry_executed(turn_id, entry_id)

        try:
            result_data = json.loads(result_str)
            if isinstance(result_data, dict):
                self._data_collector.record_transaction(
                    turn_id=turn_id,
                    entry_id=entry_id,
                    ingredient=result_data.get("ingredient", ""),
                    quantity=result_data.get("quantity", 0),
                    price=result_data.get("price", 0),
                    side=result_data.get("side", ""),
                    counterparty_id=result_data.get("counterparty_id"),
                    counterparty_name=result_data.get("counterparty_name"),
                )
        except (json.JSONDecodeError, TypeError):
            pass

    def _collect_serve_data(self, turn_id: int, arguments: dict[str, Any], result_str: str) -> None:
        """Collect serve dish results."""
        if not self._data_collector:
            return

        client_id = arguments.get("client_id", "")
        dish_name = arguments.get("dish_name", "")

        success = "error" not in result_str.lower() and "failed" not in result_str.lower()
        revenue = None

        try:
            result_data = json.loads(result_str)
            if isinstance(result_data, dict):
                revenue = result_data.get("revenue") or result_data.get("price")
                success = result_data.get("success", success)
        except (json.JSONDecodeError, TypeError):
            pass

        self._data_collector.update_order_served(
            turn_id=turn_id,
            client_id=client_id,
            dish_served=dish_name,
            success=success,
            revenue=revenue,
        )

    def call(self, name: str, arguments: dict[str, Any]) -> str:
        """Call MCP tool and return a string result for the agent."""
        out = self._call(name, arguments)
        if out.get("isError"):
            return out["content"][0]["text"] if out.get("content") else "Error"
        parts = []
        for c in out.get("content", []):
            if c.get("type") == "text":
                parts.append(c.get("text", ""))
        return "\n".join(parts) if parts else "OK"
