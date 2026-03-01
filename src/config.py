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

# Datapizza Monitoring (optional, OTLP tracing)
DATAPIZZA_OTLP_ENDPOINT = os.getenv(
    "DATAPIZZA_OTLP_ENDPOINT",
    "https://datapizza-monitoring.datapizza.tech/gateway/v1/traces",
)
DATAPIZZA_MONITORING_API_KEY = os.getenv("DATAPIZZA_MONITORING_API_KEY", "")
DATAPIZZA_PROJECT_ID = os.getenv("DATAPIZZA_PROJECT_ID", "")
# Data collection (Market Intelligence)
DB_PATH = os.getenv("HACKAPIZZA_DB_PATH", "data/hackapizza.db")

# Default target archetype when blog does not identify one (menu_decider_pre_bid format)
DEFAULT_ARCHETYPE = "Astrobarone"

# Default sentiment when the blog sentiment agent cannot classify the post
DEFAULT_SENTIMENT = "default"

# Phase-to-agent mapping for extensibility (MVP: market_broker disabled)
# Analyst runs in speaking phase AFTER menu_decider_pre_bid to analyze ingredients needed
PHASE_AGENTS = {
    "speaking": ["menu_decider_pre_bid", "analyst"],
    "closed_bid": ["auction_broker"],
    "waiting": ["menu_decider_post_bid"],
    "serving": ["maitre"],
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
