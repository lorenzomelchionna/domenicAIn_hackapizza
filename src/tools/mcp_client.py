"""HTTP client for Hackapizza game server MCP (POST /mcp with JSON-RPC)."""
from typing import Any, Callable

import requests

from src.logging_config import get_mcp_logger, log_mcp_input, log_mcp_output

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

    def __init__(self, base_url: str, api_key: str, phase_getter: Callable[[], str]):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._phase_getter = phase_getter
        self._request_id = 0

    def _get_phase(self) -> str:
        return self._phase_getter()

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
        headers = {"x-api-key": self.api_key, "Content-Type": "application/json"}
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
        return out

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
