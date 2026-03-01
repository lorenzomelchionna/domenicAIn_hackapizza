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
        """Return aggregate bid statistics per ingredient across recent turns.

        Use this to understand the general price landscape for ingredients — what
        restaurants are collectively willing to pay. Useful for calibrating initial
        bid suggestions before looking at winning-only prices.

        Args:
            window_size (int): Number of recent turns to include in the analysis (default: 2).

        Returns:
            JSON array: [{ingredient, avg_bid, min_bid, max_bid, total_bids, total_quantity}, ...]
        """
        try:
            data = queries.get_avg_bid_by_ingredient(db_path, window_size)
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @tool
    def get_winning_bid_statistics(window_size: int = 2) -> str:
        """Return bid statistics restricted to auction-winning bids per ingredient.

        Prefer this over get_bid_statistics() when deciding how much to bid to actually
        secure an ingredient. avg_winning_bid is your target; min_winning_bid shows the
        floor — bidding below it typically results in losing the auction.

        Args:
            window_size (int): Number of recent turns to include (default: 2).

        Returns:
            JSON array: [{ingredient, avg_winning_bid, min_winning_bid, max_winning_bid, winning_bids}, ...]
        """
        try:
            data = queries.get_winning_bid_stats(db_path, window_size)
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @tool
    def get_competitor_patterns(exclude_restaurant_id: int | None = None, window_size: int = 2) -> str:
        """Return per-restaurant bidding behaviour across recent turns.

        Use this to gauge how aggressively other restaurants are spending on ingredients.
        High total_spent with high avg_bid signals a strong competitor who may outbid us
        on shared ingredient needs — plan accordingly.

        Args:
            exclude_restaurant_id (int | None): Restaurant ID to exclude from results,
                typically our own ID to filter out self-data.
            window_size (int): Number of recent turns to include (default: 2).

        Returns:
            JSON array: [{restaurant_id, avg_bid, total_bids, total_quantity, total_spent}, ...]
        """
        try:
            data = queries.get_competitor_bid_patterns(db_path, exclude_restaurant_id, window_size)
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @tool
    def get_market_prices(window_size: int = 2) -> str:
        """Return price statistics for the secondary ingredient market across recent turns.

        The secondary market operates independently of the auction. Use this data to
        identify ingredients that are cheap to buy on the market (no need to overbid
        at auction) or to set competitive SELL prices when offloading surplus stock.

        Args:
            window_size (int): Number of recent turns to include (default: 2).

        Returns:
            JSON array: [{ingredient_name, avg_price, min_price, max_price, buy_count, sell_count}, ...]
        """
        try:
            data = queries.get_ingredient_market_prices(db_path, window_size)
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @tool
    def get_dish_popularity_stats(window_size: int = 2) -> str:
        """Return order and revenue statistics per dish across recent turns.

        Primary use cases:
        - Pass window_size=1 to get last-turn sales data for selecting the top 10
          best-selling dishes as this turn's draft menu (Case B draft selection).
        - Pass window_size=2+ for a broader popularity trend to identify consistently
          strong dishes across multiple turns.

        Args:
            window_size (int): Number of recent turns to include (default: 2).
                Use 1 to isolate only the immediately preceding turn.

        Returns:
            JSON array sorted by order_count descending:
            [{dish_name, order_count, avg_price, executed_count, success_rate}, ...]
        """
        try:
            data = queries.get_dish_popularity(db_path, window_size)
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @tool
    def get_competitor_status() -> str:
        """Return the latest performance snapshot for each competitor restaurant.

        Use this to assess the competitive landscape: identify which restaurants are
        wealthiest (high balance), most reputable (high reputation), or currently
        closed (potential opening to capture their missed clients).

        Returns:
            JSON array: [{restaurant_id, name, balance, reputation, is_open}, ...]
            One entry per restaurant, reflecting the most recent snapshot.
        """
        try:
            data = queries.get_competitor_performance(db_path)
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @tool
    def get_recommended_price(ingredient: str, window_size: int = 2) -> str:
        """Return a data-driven bid price recommendation for a single ingredient.

        This is the most actionable tool for bid planning: it distills historical
        winning-bid data into a single recommended_bid with a confidence signal.
        Use it ingredient-by-ingredient to build the list passed to save_suggested_bids().

        Args:
            ingredient (str): Exact name of the ingredient to analyse.
            window_size (int): Number of recent turns to include (default: 2).

        Returns:
            JSON object: {
                ingredient, recommended_bid, avg_winning_bid,
                min_winning_bid, max_winning_bid,
                confidence ("high" | "medium" | "low" | "none"),
                based_on_samples
            }
        """
        try:
            data = queries.get_recommended_bid_price(db_path, ingredient, window_size)
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @tool
    def get_available_turns() -> str:
        """Return the list of all turn IDs for which market data has been collected.

        Call this first to understand how much historical data is available before
        choosing window_size for other tools. If only one turn is available,
        use window_size=1 to avoid empty results.

        Returns:
            JSON array of integer turn IDs in ascending order: [1, 2, 3, ...]
        """
        try:
            data = queries.get_all_turns(db_path)
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @tool
    def get_turn_data_summary(turn_id: int) -> str:
        """Return a collection-completeness summary for a specific turn.

        Use this to verify that the data for a given turn is rich enough to trust.
        Low counts (e.g. bid_count=0) indicate the data collector missed that phase,
        meaning analysis tools using that turn may return unreliable results.

        Args:
            turn_id (int): The turn ID to inspect.

        Returns:
            JSON object: {
                turn_id, bid_count, meal_count, market_entry_count,
                restaurant_snapshot_count, sse_event_count
            }
        """
        try:
            data = queries.get_turn_summary(db_path, turn_id)
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @tool
    def get_ingredient_competition(window_size: int = 2) -> str:
        """Analyze ingredient competition: how contested each ingredient is.
        
        Returns JSON with: ingredient, unique_bidders, total_bids, avg_bid, min_bid, max_bid,
        bid_spread, total_quantity_demanded, competition_score (0-100, higher = harder to win).
        
        Use this to identify which ingredients are easy vs hard to acquire.
        Low competition_score = easy to win, good for menu planning.
        High competition_score = many competitors want it, bid higher or avoid.
        
        Args:
            window_size: Number of recent turns to analyze (default: 2)
        """
        try:
            data = queries.get_ingredient_competition_analysis(db_path, window_size)
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @tool
    def get_dish_profitability(recipes_json: str, window_size: int = 2) -> str:
        """Analyze dish profitability: margin between selling price and ingredient costs.
        
        IMPORTANT: Pass the recipes as a JSON string from get_recipes().
        
        Returns JSON with for each dish:
        - dish_name, avg_selling_price, estimated_ingredient_cost
        - estimated_margin, margin_percent
        - order_count (popularity), prestige
        - ingredient_competition_avg (how hard to get ingredients)
        - profitability_score (0-100, higher = better to put on menu)
        
        Use this to find dishes with HIGH margin and LOW ingredient competition.
        
        Args:
            recipes_json: JSON string of recipes (from get_recipes())
            window_size: Number of recent turns to analyze (default: 2)
        """
        try:
            recipes = json.loads(recipes_json)
            data = queries.get_dish_profitability_analysis(db_path, recipes, window_size)
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @tool
    def get_strategic_dish_ranking(recipes_json: str, window_size: int = 2) -> str:
        """Get strategic ranking of dishes for optimal menu selection.
        
        IMPORTANT: Pass the recipes as a JSON string from get_recipes().
        
        Combines profitability, competition, demand, AND ingredient synergies.
        Dishes that share ingredients with other good dishes get bonus points
        (more efficient bidding at auction).
        
        Returns JSON sorted by final_score (highest = best menu candidates):
        - All fields from get_dish_profitability
        - ingredient_synergy_score: how many other dishes share ingredients
        - final_score: composite score including synergy bonus
        
        Use this to select the TOP 10 dishes for your draft menu.
        
        Args:
            recipes_json: JSON string of recipes (from get_recipes())
            window_size: Number of recent turns to analyze (default: 2)
        """
        try:
            recipes = json.loads(recipes_json)
            data = queries.get_strategic_dish_ranking(db_path, recipes, window_size)
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @tool
    def get_menu_popularity(window_size: int = 2) -> str:
        """Get dish popularity based on competitor menus - which dishes other restaurants offer.
        
        Analyzes what dishes appear on other restaurants' menus. If many restaurants
        offer the same dish, it's likely popular with customers (high demand signal).
        
        Returns JSON sorted by restaurant_count (most popular first):
        - dish_name: name of the dish
        - restaurant_count: how many restaurants have it on their menu
        - avg_price: average price across all menus
        - min_price: lowest price seen
        - max_price: highest price seen
        - restaurants: list of restaurant names offering this dish
        
        Use this to:
        - Identify trending dishes that customers want
        - See competitor pricing for the same dish
        - Find underserved niches (dishes few competitors offer)
        
        Args:
            window_size: Number of recent turns to analyze (default: 2)
        """
        try:
            data = queries.get_menu_popularity(db_path, window_size)
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @tool
    def get_competitor_menu_prices(dish_names_json: str | None = None, window_size: int = 2) -> str:
        """Get competitor pricing for specific dishes from the last N turns.

        EXCLUDES our own restaurant from results. Use this to see what OTHER restaurants
        charge for the same dishes you plan to offer. Essential for competitive pricing.

        Args:
            dish_names_json (str | None): Optional JSON array of dish names to filter.
                If provided, only returns pricing for those specific dishes.
                If None, returns all dishes from competitor menus.
            window_size (int): Number of recent turns to analyze (default: 2).

        Returns:
            JSON array sorted by dish_name:
            [{
                dish_name: str,
                competitor_count: int (how many competitors offer this dish),
                avg_price: float,
                min_price: float,
                max_price: float,
                price_details: [{restaurant: str, restaurant_id: int, price: float, turn_id: int}, ...]
            }, ...]
        """
        try:
            # Get our restaurant_id from state to exclude ourselves
            exclude_id = None
            if state_getter:
                state = state_getter()
                exclude_id = state.restaurant_id if state.restaurant_id else None
            
            all_menu_data = queries.get_competitor_menu_prices(
                db_path, 
                exclude_restaurant_id=exclude_id,
                window_size=window_size
            )
            
            filter_dishes = None
            if dish_names_json:
                filter_dishes = set(json.loads(dish_names_json))
            
            results = []
            for item in all_menu_data:
                dish_name = item.get("dish_name", "")
                if filter_dishes and dish_name not in filter_dishes:
                    continue
                
                results.append(item)
            
            return json.dumps(results, ensure_ascii=False)
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
        get_ingredient_competition,
        get_dish_profitability,
        get_strategic_dish_ranking,
        get_menu_popularity,
        get_competitor_menu_prices,
    ]
    by_name = {t.__name__: t for t in all_tools}
    return all_tools, by_name
