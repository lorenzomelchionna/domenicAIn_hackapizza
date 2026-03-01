"""Data collection module for Market Intelligence."""
from .collector import DataCollector
from .db import get_connection, init_db
from .queries import (
    DEFAULT_WINDOW_SIZE,
    blog_post_exists,
    get_all_turns,
    get_avg_bid_by_ingredient,
    get_competitor_balance_trend,
    get_competitor_bid_patterns,
    get_competitor_performance,
    get_dish_popularity,
    get_ingredient_market_prices,
    get_recent_turns_with_bids,
    get_recommended_bid_price,
    get_turn_summary,
    get_winning_bid_stats,
    record_blog_post,
)

__all__ = [
    "DataCollector",
    "blog_post_exists",
    "init_db",
    "get_connection",
    "record_blog_post",
    "DEFAULT_WINDOW_SIZE",
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
    "get_recent_turns_with_bids",
]
