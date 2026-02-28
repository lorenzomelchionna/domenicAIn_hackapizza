"""HTTP client for Hackapizza game server MCP (POST /mcp with JSON-RPC)."""
from typing import Any, Callable

import requests

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
        phase = self._get_phase()
        allowed = TOOL_PHASES.get(name, [])
        if allowed and phase not in allowed:
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Tool {name} not allowed in phase {phase}. Allowed phases: {allowed}"}],
            }

        # update_restaurant_is_open: in serving, only close (is_open=false) allowed
        if name == "update_restaurant_is_open" and phase == "serving":
            if arguments.get("is_open", True):
                return {
                    "isError": True,
                    "content": [{"type": "text", "text": "In serving phase, can only close (is_open=false), not reopen."}],
                }

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
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"MCP request failed: {e}"}],
            }

        if "error" in data:
            return {
                "isError": True,
                "content": [{"type": "text", "text": str(data["error"])}],
            }

        result = data.get("result", {})
        if isinstance(result, dict) and result.get("isError"):
            text = ""
            for c in result.get("content", []):
                if c.get("type") == "text":
                    text += c.get("text", "")
            return {"isError": True, "content": [{"type": "text", "text": text or "Unknown error"}]}

        return result if isinstance(result, dict) else {"content": [{"type": "text", "text": str(result)}]}

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
