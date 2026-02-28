"""SSE listener for Hackapizza game events. Dispatches to orchestrator."""
import asyncio
import json
from datetime import datetime
from typing import Any, Awaitable, Callable

import aiohttp


def log(tag: str, message: str) -> None:
    print(f"[{tag}] {datetime.now()}: {message}")


async def handle_line(
    raw_line: bytes,
    dispatch: Callable[[str, dict[str, Any]], Awaitable[None]],
) -> None:
    """Parse SSE line and dispatch event."""
    if not raw_line:
        return
    line = raw_line.decode("utf-8", errors="ignore").strip()
    if not line:
        return
    if line.startswith("data:"):
        payload = line[5:].strip()
        if payload == "connected":
            log("SSE", "connected")
            return
        line = payload
    try:
        event_json = json.loads(line)
    except json.JSONDecodeError:
        log("SSE", f"raw: {line}")
        return
    event_type = event_json.get("type", "unknown")
    event_data = event_json.get("data", {})
    if isinstance(event_data, dict):
        await dispatch(event_type, event_data)
    else:
        await dispatch(event_type, {"value": event_data})


async def listen(
    base_url: str,
    api_key: str,
    team_id: int,
    dispatch: Callable[[str, dict[str, Any]], Awaitable[None]],
) -> None:
    """Connect to SSE stream and dispatch events. Runs until connection drops."""
    url = f"{base_url.rstrip('/')}/events/{team_id}"
    headers = {"Accept": "text/event-stream", "x-api-key": api_key}
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=15, sock_read=None)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, headers=headers) as response:
            response.raise_for_status()
            log("SSE", "connection open")
            async for line in response.content:
                await handle_line(line, dispatch)
    log("SSE", "connection closed")
