"""Monitor state persistence for Streamlit dashboard. Writes game state and event log to JSON."""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.state.game_state import GameState

LOG_DIR = Path(os.getenv("HACKAPIZZA_LOG_DIR", "logs"))
MONITOR_STATE_PATH = LOG_DIR / "monitor_state.json"
MAX_EVENT_LOG_ENTRIES = 100


def _state_to_dict(state: "GameState") -> dict[str, Any]:
    """Serialize GameState to JSON-serializable dict."""
    return {
        "phase": state.phase,
        "turn_id": state.turn_id,
        "restaurant_id": state.restaurant_id,
        "balance": state.balance,
        "reputation": state.reputation,
        "inventory": state.inventory,
        "menu": state.menu,
        "recipes_count": len(state.recipes),
        "recipes": state.recipes,
        "pending_clients": state.pending_clients,
        "prepared_dishes": [list(p) for p in state.prepared_dishes],
        "market_entries": state.market_entries,
        "is_open": state.is_open,
        "restaurants_count": len(state.restaurants),
        "draft_menu": state.draft_menu,
        "suggested_bids": [{"ingredient": ing, "price": p} for ing, p in state.suggested_bids],
        "actual_bids": state.actual_bids,
    }


def write_monitor_state(state: "GameState", event_log: list[dict[str, Any]]) -> None:
    """Write current state and event log to JSON file for Streamlit dashboard."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now().isoformat(),
        "state": _state_to_dict(state),
        "event_log": event_log[-MAX_EVENT_LOG_ENTRIES:],
    }
    with open(MONITOR_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, default=str)


def read_monitor_state() -> dict[str, Any] | None:
    """Read monitor state from file. Returns None if file does not exist or is invalid."""
    if not MONITOR_STATE_PATH.exists():
        return None
    try:
        with open(MONITOR_STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
