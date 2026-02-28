"""Logging configuration: separate file handlers for SSE and MCP."""
import json
import logging
import os
from pathlib import Path

LOG_DIR = Path(os.getenv("HACKAPIZZA_LOG_DIR", "logs"))
SSE_LOG_FILE = LOG_DIR / "sse.log"
MCP_LOG_FILE = LOG_DIR / "mcp.log"


def _ensure_log_dir() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def setup_loggers() -> None:
    """Configure SSE and MCP loggers with dedicated file handlers."""
    _ensure_log_dir()

    # SSE logger
    sse_logger = logging.getLogger("hackapizza.sse")
    sse_logger.setLevel(logging.DEBUG)
    sse_logger.handlers.clear()
    sse_handler = logging.FileHandler(SSE_LOG_FILE, encoding="utf-8")
    sse_handler.setLevel(logging.DEBUG)
    sse_handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    sse_logger.addHandler(sse_handler)
    sse_logger.propagate = False

    # MCP logger
    mcp_logger = logging.getLogger("hackapizza.mcp")
    mcp_logger.setLevel(logging.DEBUG)
    mcp_logger.handlers.clear()
    mcp_handler = logging.FileHandler(MCP_LOG_FILE, encoding="utf-8")
    mcp_handler.setLevel(logging.DEBUG)
    mcp_handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    mcp_logger.addHandler(mcp_handler)
    mcp_logger.propagate = False


def get_sse_logger() -> logging.Logger:
    return logging.getLogger("hackapizza.sse")


def get_mcp_logger() -> logging.Logger:
    return logging.getLogger("hackapizza.mcp")


def log_sse_input(logger: logging.Logger, raw: bytes) -> None:
    """Log raw SSE input."""
    try:
        text = raw.decode("utf-8", errors="replace").strip()
        logger.debug("INPUT (raw): %s", repr(text) if text else "<empty>")
    except Exception:
        logger.debug("INPUT (raw): %s", repr(raw))


def log_sse_output(logger: logging.Logger, event_type: str, event_data: dict) -> None:
    """Log parsed SSE output (event dispatched)."""
    logger.debug("OUTPUT | type=%s | data=%s", event_type, json.dumps(event_data, default=str))


def log_mcp_input(logger: logging.Logger, tool_name: str, arguments: dict) -> None:
    """Log MCP call input."""
    logger.debug("INPUT | tool=%s | arguments=%s", tool_name, json.dumps(arguments, default=str))


def log_mcp_output(logger: logging.Logger, tool_name: str, result: str, is_error: bool = False) -> None:
    """Log MCP call output."""
    level = "ERROR" if is_error else "OUTPUT"
    logger.debug("%s | tool=%s | result=%s", level, tool_name, result)
