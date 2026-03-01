"""Static data and configuration files for Hackapizza 2.0."""
import json
from functools import lru_cache
from pathlib import Path

_DATA_DIR = Path(__file__).parent


@lru_cache(maxsize=None)
def load_json(name: str) -> dict | list:
    """Load and cache a JSON file from the data directory."""
    with open(_DATA_DIR / name) as f:
        return json.load(f)
