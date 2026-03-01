"""@tool wrappers for Market Intelligence queries. Used by the Analyst agent."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from datapizza.tools import tool

from src.data_collector import queries


def create_analyst_tools(db_path: str | Path, state_getter: Callable | None = None) -> tuple[list, dict]:
    """Create analyst tool functions bound to the given database path."""
    
    @tool
    def get_bid_statistics(window_size: int = 2) -> str:
        """Get average bid statistics per ingredient from recent turns.
        
        Returns JSON with: ingredient, avg_bid, min_bid, max_bid, total_bids, total_quantity.
        Use this to understand what prices are being paid for each ingredient.
        
        Args:
            window_size: Number of recent turns to analyze (default: 2)
        """
        try:
            data = queries.get_avg_bid_by_ingredient(db_path, window_size)
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @tool
    def get_winning_bid_statistics(window_size: int = 2) -> str:
        """Get winning bid statistics per ingredient from recent turns.
        
        Returns JSON with: ingredient, avg_winning_bid, min_winning_bid, max_winning_bid, winning_bids.
        Use this to understand the minimum price needed to WIN an auction.
        
        Args:
            window_size: Number of recent turns to analyze (default: 2)
        """
        try:
            data = queries.get_winning_bid_stats(db_path, window_size)
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @tool
    def get_competitor_patterns(exclude_restaurant_id: int | None = None, window_size: int = 2) -> str:
        """Get competitor bidding patterns from recent turns.
        
        Returns JSON with: restaurant_id, avg_bid, total_bids, total_quantity, total_spent.
        Use this to understand how aggressive competitors are bidding.
        
        Args:
            exclude_restaurant_id: Optional restaurant ID to exclude (e.g., our own)
            window_size: Number of recent turns to analyze (default: 2)
        """
        try:
            data = queries.get_competitor_bid_patterns(db_path, exclude_restaurant_id, window_size)
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @tool
    def get_market_prices(window_size: int = 2) -> str:
        """Get market price statistics per ingredient from recent turns.
        
        Returns JSON with: ingredient_name, avg_price, min_price, max_price, buy_count, sell_count.
        Use this to understand market (secondary) prices for ingredients.
        
        Args:
            window_size: Number of recent turns to analyze (default: 2)
        """
        try:
            data = queries.get_ingredient_market_prices(db_path, window_size)
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @tool
    def get_dish_popularity_stats(window_size: int = 2) -> str:
        """Get dish popularity statistics from recent turns.
        
        Returns JSON with: dish_name, order_count, avg_price, executed_count, success_rate.
        Use this to understand which dishes are popular and profitable.
        
        Args:
            window_size: Number of recent turns to analyze (default: 2)
        """
        try:
            data = queries.get_dish_popularity(db_path, window_size)
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @tool
    def get_competitor_status() -> str:
        """Get current competitor performance (latest snapshot per restaurant).
        
        Returns JSON with: restaurant_id, name, balance, reputation, is_open.
        Use this to understand competitor financial status and reputation.
        """
        try:
            data = queries.get_competitor_performance(db_path)
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @tool
    def get_recommended_price(ingredient: str, window_size: int = 2) -> str:
        """Get recommended bid price for a specific ingredient based on historical data.
        
        Returns JSON with: ingredient, recommended_bid, avg_winning_bid, min_winning_bid, 
        max_winning_bid, confidence (high/medium/low/none), based_on_samples.
        
        Args:
            ingredient: Name of the ingredient to get recommendation for
            window_size: Number of recent turns to analyze (default: 2)
        """
        try:
            data = queries.get_recommended_bid_price(db_path, ingredient, window_size)
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @tool
    def get_available_turns() -> str:
        """Get list of all turn IDs with collected market data.
        
        Returns JSON array of turn IDs. Use this to understand data availability.
        """
        try:
            data = queries.get_all_turns(db_path)
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @tool
    def get_turn_data_summary(turn_id: int) -> str:
        """Get a summary of data collected for a specific turn.
        
        Returns JSON with: turn_id, bid_count, meal_count, market_entry_count, 
        restaurant_snapshot_count, sse_event_count.
        
        Args:
            turn_id: The turn ID to get summary for
        """
        try:
            data = queries.get_turn_summary(db_path, turn_id)
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    all_tools = [
        get_bid_statistics,
        get_winning_bid_statistics,
        get_competitor_patterns,
        get_market_prices,
        get_dish_popularity_stats,
        get_competitor_status,
        get_recommended_price,
        get_available_turns,
        get_turn_data_summary,
    ]
    by_name = {t.__name__: t for t in all_tools}
    return all_tools, by_name
