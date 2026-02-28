"""Query functions for Market Intelligence analysis."""
from pathlib import Path
from typing import Any

from .db import get_connection


def get_avg_bid_by_ingredient(db_path: str | Path) -> list[dict[str, Any]]:
    """Get average bid amount per ingredient across all turns.
    
    Returns list of dicts with: ingredient, avg_bid, min_bid, max_bid, total_bids, win_rate
    """
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """
            SELECT 
                ingredient,
                ROUND(AVG(bid_amount), 2) as avg_bid,
                MIN(bid_amount) as min_bid,
                MAX(bid_amount) as max_bid,
                COUNT(*) as total_bids,
                ROUND(AVG(CASE WHEN won = 1 THEN 1.0 ELSE 0.0 END) * 100, 1) as win_rate
            FROM bid_history
            GROUP BY ingredient
            ORDER BY avg_bid DESC
            """
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_winning_bid_stats(db_path: str | Path) -> list[dict[str, Any]]:
    """Get statistics on winning bids per ingredient.
    
    Returns list of dicts with: ingredient, avg_winning_bid, min_winning_bid, max_winning_bid
    """
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """
            SELECT 
                ingredient,
                ROUND(AVG(bid_amount), 2) as avg_winning_bid,
                MIN(bid_amount) as min_winning_bid,
                MAX(bid_amount) as max_winning_bid,
                COUNT(*) as winning_bids
            FROM bid_history
            WHERE won = 1
            GROUP BY ingredient
            ORDER BY avg_winning_bid DESC
            """
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_competitor_bid_patterns(db_path: str | Path, exclude_restaurant_id: int | None = None) -> list[dict[str, Any]]:
    """Get bidding patterns of competitors.
    
    Returns list of dicts with: restaurant_id, avg_bid, total_bids, win_rate, total_spent
    """
    conn = get_connection(db_path)
    try:
        query = """
            SELECT 
                restaurant_id,
                ROUND(AVG(bid_amount), 2) as avg_bid,
                COUNT(*) as total_bids,
                ROUND(AVG(CASE WHEN won = 1 THEN 1.0 ELSE 0.0 END) * 100, 1) as win_rate,
                SUM(CASE WHEN won = 1 THEN bid_amount * quantity ELSE 0 END) as total_spent
            FROM bid_history
        """
        params: tuple = ()
        if exclude_restaurant_id is not None:
            query += " WHERE restaurant_id != ?"
            params = (exclude_restaurant_id,)
        query += " GROUP BY restaurant_id ORDER BY win_rate DESC"
        
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_ingredient_market_prices(db_path: str | Path) -> list[dict[str, Any]]:
    """Get market price statistics per ingredient.
    
    Returns list of dicts with: ingredient_name, avg_price, min_price, max_price, buy_count, sell_count
    """
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """
            SELECT 
                ingredient_name,
                ROUND(AVG(price), 2) as avg_price,
                MIN(price) as min_price,
                MAX(price) as max_price,
                SUM(CASE WHEN side = 'BUY' THEN 1 ELSE 0 END) as buy_count,
                SUM(CASE WHEN side = 'SELL' THEN 1 ELSE 0 END) as sell_count
            FROM market_entries
            GROUP BY ingredient_name
            ORDER BY avg_price DESC
            """
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_dish_popularity(db_path: str | Path) -> list[dict[str, Any]]:
    """Get dish popularity based on orders.
    
    Returns list of dicts with: dish_name, order_count, avg_price, executed_count, success_rate
    """
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """
            SELECT 
                dish_name,
                COUNT(*) as order_count,
                ROUND(AVG(price), 2) as avg_price,
                SUM(CASE WHEN executed = 1 THEN 1 ELSE 0 END) as executed_count,
                ROUND(AVG(CASE WHEN executed = 1 THEN 1.0 ELSE 0.0 END) * 100, 1) as success_rate
            FROM meals
            WHERE dish_name IS NOT NULL AND dish_name != ''
            GROUP BY dish_name
            ORDER BY order_count DESC
            """
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_competitor_performance(db_path: str | Path) -> list[dict[str, Any]]:
    """Get competitor performance over time (latest snapshot per restaurant).
    
    Returns list of dicts with: restaurant_id, name, balance, reputation, is_open
    """
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """
            SELECT 
                rs.restaurant_id,
                rs.name,
                rs.balance,
                rs.reputation,
                rs.is_open,
                rs.turn_id as last_turn
            FROM restaurant_snapshots rs
            INNER JOIN (
                SELECT restaurant_id, MAX(turn_id) as max_turn
                FROM restaurant_snapshots
                GROUP BY restaurant_id
            ) latest ON rs.restaurant_id = latest.restaurant_id AND rs.turn_id = latest.max_turn
            ORDER BY rs.reputation DESC
            """
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_competitor_balance_trend(db_path: str | Path, restaurant_id: int) -> list[dict[str, Any]]:
    """Get balance trend for a specific competitor.
    
    Returns list of dicts with: turn_id, balance, reputation
    """
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """
            SELECT turn_id, balance, reputation
            FROM restaurant_snapshots
            WHERE restaurant_id = ?
            ORDER BY turn_id ASC
            """,
            (restaurant_id,),
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_recommended_bid_price(db_path: str | Path, ingredient: str) -> dict[str, Any]:
    """Get recommended bid price for an ingredient based on historical winning bids.
    
    Returns dict with: ingredient, recommended_bid, confidence, based_on_samples
    """
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """
            SELECT 
                AVG(bid_amount) as avg_winning,
                MIN(bid_amount) as min_winning,
                MAX(bid_amount) as max_winning,
                COUNT(*) as samples
            FROM bid_history
            WHERE ingredient = ? AND won = 1
            """,
            (ingredient,),
        )
        row = cursor.fetchone()
        if row and row["samples"] and row["samples"] > 0:
            avg = row["avg_winning"]
            recommended = round(avg * 1.1, 2)  # 10% above average winning bid
            confidence = "high" if row["samples"] >= 10 else "medium" if row["samples"] >= 5 else "low"
            return {
                "ingredient": ingredient,
                "recommended_bid": recommended,
                "avg_winning_bid": round(avg, 2),
                "min_winning_bid": row["min_winning"],
                "max_winning_bid": row["max_winning"],
                "confidence": confidence,
                "based_on_samples": row["samples"],
            }
        return {
            "ingredient": ingredient,
            "recommended_bid": None,
            "confidence": "none",
            "based_on_samples": 0,
        }
    finally:
        conn.close()


def get_turn_summary(db_path: str | Path, turn_id: int) -> dict[str, Any]:
    """Get a summary of data collected for a specific turn.
    
    Returns dict with counts and key metrics for the turn.
    """
    conn = get_connection(db_path)
    try:
        summary: dict[str, Any] = {"turn_id": turn_id}
        
        cursor = conn.execute("SELECT COUNT(*) as c FROM bid_history WHERE turn_id = ?", (turn_id,))
        summary["bid_count"] = cursor.fetchone()["c"]
        
        cursor = conn.execute("SELECT COUNT(*) as c FROM meals WHERE turn_id = ?", (turn_id,))
        summary["meal_count"] = cursor.fetchone()["c"]
        
        cursor = conn.execute("SELECT COUNT(*) as c FROM market_entries WHERE turn_id = ?", (turn_id,))
        summary["market_entry_count"] = cursor.fetchone()["c"]
        
        cursor = conn.execute("SELECT COUNT(*) as c FROM restaurant_snapshots WHERE turn_id = ?", (turn_id,))
        summary["restaurant_snapshot_count"] = cursor.fetchone()["c"]
        
        cursor = conn.execute("SELECT COUNT(*) as c FROM sse_events WHERE turn_id = ?", (turn_id,))
        summary["sse_event_count"] = cursor.fetchone()["c"]
        
        return summary
    finally:
        conn.close()


def get_all_turns(db_path: str | Path) -> list[int]:
    """Get list of all turn IDs with collected data."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """
            SELECT DISTINCT turn_id FROM (
                SELECT turn_id FROM bid_history
                UNION SELECT turn_id FROM meals
                UNION SELECT turn_id FROM market_entries
                UNION SELECT turn_id FROM restaurant_snapshots
                UNION SELECT turn_id FROM sse_events WHERE turn_id IS NOT NULL
            ) ORDER BY turn_id
            """
        )
        return [row["turn_id"] for row in cursor.fetchall()]
    finally:
        conn.close()
