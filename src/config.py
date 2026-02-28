"""Configuration for Hackapizza 2.0 multi-agent system."""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Game server
TEAM_ID = int(os.getenv("TEAM_ID", "0"))
TEAM_API_KEY = os.getenv("TEAM_API_KEY", "")
BASE_URL = os.getenv("HACKAPIZZA_BASE_URL", "https://hackapizza.datapizza.tech")

# LLM (Regolo.ai)
REGOLO_API_KEY = os.getenv("REGOLO_API_KEY", "")
REGOLO_MODEL = os.getenv("REGOLO_MODEL", "gpt-oss-120b")
REGOLO_BASE_URL = "https://api.regolo.ai/v1"

# Phase-to-agent mapping for extensibility
PHASE_AGENTS = {
    "speaking": ["diplomatico", "menu_decider_pre_bid", "market_broker"],
    "closed_bid": ["menu_decider_pre_bid", "auction_broker", "market_broker"],
    "waiting": ["menu_decider_post_bid", "market_broker"],
    "serving": ["maitre", "market_broker"],
    "stopped": [],
}


def validate_config() -> None:
    """Raise if required config is missing."""
    if not TEAM_API_KEY or TEAM_API_KEY == "your_team_api_key":
        raise ValueError("Set TEAM_API_KEY in .env")
    if TEAM_ID <= 0:
        raise ValueError("Set TEAM_ID in .env (positive integer)")
    if not REGOLO_API_KEY:
        raise ValueError("Set REGOLO_API_KEY in .env for LLM")
