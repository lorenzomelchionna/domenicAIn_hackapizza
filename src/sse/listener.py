"""SSE listener for Hackapizza game events. Dispatches to orchestrator."""
import asyncio
import json
from datetime import datetime
from typing import Any, Awaitable, Callable

import aiohttp

from src.logging_config import get_sse_logger, log_sse_input, log_sse_output


def log(tag: str, message: str) -> None:
    print(f"[{tag}] {datetime.now()}: {message}")


async def handle_line(
    raw_line: bytes,
    dispatch: Callable[[str, dict[str, Any]], Awaitable[None]],
) -> None:
    """Parse SSE line and dispatch event."""
    sse_logger = get_sse_logger()
    if not raw_line:
        return
    log_sse_input(sse_logger, raw_line)
    line = raw_line.decode("utf-8", errors="ignore").strip()
    if not line:
        return
    if line.startswith("data:"):
        payload = line[5:].strip()
        if payload == "connected":
            log("SSE", "connected")
            sse_logger.debug("OUTPUT | type=connected | data={}")
            return
        line = payload
    try:
        event_json = json.loads(line)
    except json.JSONDecodeError:
        log("SSE", f"raw: {line}")
        sse_logger.debug("OUTPUT | type=parse_error | data=%s", repr(line))
        return
    event_type = event_json.get("type", "unknown")
    event_data = event_json.get("data", {})
    if not isinstance(event_data, dict):
        event_data = {"value": event_data}
    log_sse_output(sse_logger, event_type, event_data)
    await dispatch(event_type, event_data)


async def listen(
    base_url: str,
    api_key: str,
    team_id: int,
    dispatch: Callable[[str, dict[str, Any]], Awaitable[None]],
) -> None:
    """Connect to SSE stream and dispatch events. Runs until connection drops."""
    sse_logger = get_sse_logger()
    url = f"{base_url.rstrip('/')}/events/{team_id}"
    headers = {"Accept": "text/event-stream", "x-api-key": api_key}
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=15, sock_read=None)
    sse_logger.debug("INPUT | connect url=%s team_id=%s", url, team_id)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, headers=headers) as response:
            response.raise_for_status()
            log("SSE", "connection open")
            sse_logger.debug("OUTPUT | connection open | status=%s", response.status)
            try:
                async for line in response.content:
                    await handle_line(line, dispatch)
            except aiohttp.ClientPayloadError as e:
                sse_logger.debug("OUTPUT | connection closed (payload incomplete): %s", str(e))
            except asyncio.CancelledError:
                raise
            except Exception as e:
                sse_logger.debug("OUTPUT | connection error: %s", str(e))
    log("SSE", "connection closed")
    sse_logger.debug("OUTPUT | connection closed")
