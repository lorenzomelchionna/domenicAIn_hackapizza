"""Data collection module for Market Intelligence."""
from .collector import DataCollector
from .db import get_connection, init_db
from .queries import (
    get_all_turns,
    get_avg_bid_by_ingredient,
    get_competitor_balance_trend,
    get_competitor_bid_patterns,
    get_competitor_performance,
    get_dish_popularity,
    get_ingredient_market_prices,
    get_recommended_bid_price,
    get_turn_summary,
    get_winning_bid_stats,
)

__all__ = [
    "DataCollector",
    "init_db",
    "get_connection",
    "get_avg_bid_by_ingredient",
    "get_winning_bid_stats",
    "get_competitor_bid_patterns",
    "get_ingredient_market_prices",
    "get_dish_popularity",
    "get_competitor_performance",
    "get_competitor_balance_trend",
    "get_recommended_bid_price",
    "get_turn_summary",
    "get_all_turns",
]
