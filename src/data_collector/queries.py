"""Query functions for Market Intelligence analysis with sliding window support."""
from pathlib import Path
from typing import Any

from .db import get_connection

DEFAULT_WINDOW_SIZE = 2


def _get_recent_turns(conn, window_size: int = DEFAULT_WINDOW_SIZE) -> list[int]:
    """Get the most recent N turn IDs with bid_history data."""
    cursor = conn.execute(
        """
        SELECT DISTINCT turn_id FROM bid_history
        ORDER BY turn_id DESC
        LIMIT ?
        """,
        (window_size,),
    )
    return [row["turn_id"] for row in cursor.fetchall()]


def _get_recent_turns_any(conn, window_size: int = DEFAULT_WINDOW_SIZE) -> list[int]:
    """Get the most recent N turn IDs from any table."""
    cursor = conn.execute(
        """
        SELECT DISTINCT turn_id FROM (
            SELECT turn_id FROM bid_history
            UNION SELECT turn_id FROM meals
            UNION SELECT turn_id FROM market_entries
            UNION SELECT turn_id FROM restaurant_snapshots
            UNION SELECT turn_id FROM sse_events WHERE turn_id IS NOT NULL
        ) ORDER BY turn_id DESC
        LIMIT ?
        """,
        (window_size,),
    )
    return [row["turn_id"] for row in cursor.fetchall()]


def get_avg_bid_by_ingredient(db_path: str | Path, window_size: int = DEFAULT_WINDOW_SIZE) -> list[dict[str, Any]]:
    """Get average bid amount per ingredient for the last N turns.
    
    NOTE: bid_history API only returns winning bids, so all records are won=1.
    
    Returns list of dicts with: ingredient, avg_bid, min_bid, max_bid, total_bids, total_quantity
    """
    conn = get_connection(db_path)
    try:
        recent_turns = _get_recent_turns(conn, window_size)
        if not recent_turns:
            return []
        
        placeholders = ",".join("?" * len(recent_turns))
        cursor = conn.execute(
            f"""
            SELECT 
                ingredient,
                ROUND(AVG(bid_amount), 2) as avg_bid,
                MIN(bid_amount) as min_bid,
                MAX(bid_amount) as max_bid,
                COUNT(*) as total_bids,
                SUM(quantity) as total_quantity
            FROM bid_history
            WHERE turn_id IN ({placeholders})
            GROUP BY ingredient
            ORDER BY avg_bid DESC
            """,
            recent_turns,
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_winning_bid_stats(db_path: str | Path, window_size: int = DEFAULT_WINDOW_SIZE) -> list[dict[str, Any]]:
    """Get statistics on winning bids per ingredient for the last N turns.
    
    Returns list of dicts with: ingredient, avg_winning_bid, min_winning_bid, max_winning_bid
    """
    conn = get_connection(db_path)
    try:
        recent_turns = _get_recent_turns(conn, window_size)
        if not recent_turns:
            return []
        
        placeholders = ",".join("?" * len(recent_turns))
        cursor = conn.execute(
            f"""
            SELECT 
                ingredient,
                ROUND(AVG(bid_amount), 2) as avg_winning_bid,
                MIN(bid_amount) as min_winning_bid,
                MAX(bid_amount) as max_winning_bid,
                COUNT(*) as winning_bids
            FROM bid_history
            WHERE won = 1 AND turn_id IN ({placeholders})
            GROUP BY ingredient
            ORDER BY avg_winning_bid DESC
            """,
            recent_turns,
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_competitor_bid_patterns(db_path: str | Path, exclude_restaurant_id: int | None = None, window_size: int = DEFAULT_WINDOW_SIZE) -> list[dict[str, Any]]:
    """Get bidding patterns of competitors for the last N turns.
    
    NOTE: bid_history API only returns winning bids, so total_spent = all bids (all are won).
    
    Returns list of dicts with: restaurant_id, avg_bid, total_bids, total_quantity, total_spent
    """
    conn = get_connection(db_path)
    try:
        recent_turns = _get_recent_turns(conn, window_size)
        if not recent_turns:
            return []
        
        placeholders = ",".join("?" * len(recent_turns))
        params: list = list(recent_turns)
        
        query = f"""
            SELECT 
                restaurant_id,
                ROUND(AVG(bid_amount), 2) as avg_bid,
                COUNT(*) as total_bids,
                SUM(quantity) as total_quantity,
                ROUND(SUM(bid_amount * quantity), 2) as total_spent
            FROM bid_history
            WHERE turn_id IN ({placeholders})
        """
        
        if exclude_restaurant_id is not None:
            query += " AND restaurant_id != ?"
            params.append(exclude_restaurant_id)
        
        query += " GROUP BY restaurant_id ORDER BY total_spent DESC"
        
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_ingredient_market_prices(db_path: str | Path, window_size: int = DEFAULT_WINDOW_SIZE) -> list[dict[str, Any]]:
    """Get market price statistics per ingredient for the last N turns.
    
    Returns list of dicts with: ingredient_name, avg_price, min_price, max_price, buy_count, sell_count
    """
    conn = get_connection(db_path)
    try:
        recent_turns = _get_recent_turns_any(conn, window_size)
        if not recent_turns:
            return []
        
        placeholders = ",".join("?" * len(recent_turns))
        cursor = conn.execute(
            f"""
            SELECT 
                ingredient_name,
                ROUND(AVG(price), 2) as avg_price,
                MIN(price) as min_price,
                MAX(price) as max_price,
                SUM(CASE WHEN side = 'BUY' THEN 1 ELSE 0 END) as buy_count,
                SUM(CASE WHEN side = 'SELL' THEN 1 ELSE 0 END) as sell_count
            FROM market_entries
            WHERE turn_id IN ({placeholders})
            GROUP BY ingredient_name
            ORDER BY avg_price DESC
            """,
            recent_turns,
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_dish_popularity(db_path: str | Path, window_size: int = DEFAULT_WINDOW_SIZE) -> list[dict[str, Any]]:
    """Get dish popularity based on orders for the last N turns.
    
    Returns list of dicts with: dish_name, order_count, avg_price, executed_count, success_rate
    """
    conn = get_connection(db_path)
    try:
        recent_turns = _get_recent_turns_any(conn, window_size)
        if not recent_turns:
            return []
        
        placeholders = ",".join("?" * len(recent_turns))
        cursor = conn.execute(
            f"""
            SELECT 
                dish_name,
                COUNT(*) as order_count,
                ROUND(AVG(price), 2) as avg_price,
                SUM(CASE WHEN executed = 1 THEN 1 ELSE 0 END) as executed_count,
                ROUND(AVG(CASE WHEN executed = 1 THEN 1.0 ELSE 0.0 END) * 100, 1) as success_rate
            FROM meals
            WHERE dish_name IS NOT NULL AND dish_name != '' AND turn_id IN ({placeholders})
            GROUP BY dish_name
            ORDER BY order_count DESC
            """,
            recent_turns,
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_competitor_performance(db_path: str | Path) -> list[dict[str, Any]]:
    """Get competitor performance (latest snapshot per restaurant).
    
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
                SELECT restaurant_id, MAX(id) as max_id
                FROM restaurant_snapshots
                GROUP BY restaurant_id
            ) latest ON rs.id = latest.max_id
            ORDER BY rs.reputation DESC
            """
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_competitor_balance_trend(db_path: str | Path, restaurant_id: int, window_size: int = DEFAULT_WINDOW_SIZE) -> list[dict[str, Any]]:
    """Get balance trend for a specific competitor for the last N turns.
    
    Returns list of dicts with: turn_id, balance, reputation
    """
    conn = get_connection(db_path)
    try:
        recent_turns = _get_recent_turns_any(conn, window_size)
        if not recent_turns:
            return []
        
        placeholders = ",".join("?" * len(recent_turns))
        cursor = conn.execute(
            f"""
            SELECT turn_id, balance, reputation
            FROM restaurant_snapshots
            WHERE restaurant_id = ? AND turn_id IN ({placeholders})
            ORDER BY turn_id ASC
            """,
            [restaurant_id] + recent_turns,
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_recommended_bid_price(db_path: str | Path, ingredient: str, window_size: int = DEFAULT_WINDOW_SIZE) -> dict[str, Any]:
    """Get recommended bid price for an ingredient based on recent winning bids.
    
    Returns dict with: ingredient, recommended_bid, confidence, based_on_samples
    """
    conn = get_connection(db_path)
    try:
        recent_turns = _get_recent_turns(conn, window_size)
        if not recent_turns:
            return {
                "ingredient": ingredient,
                "recommended_bid": None,
                "confidence": "none",
                "based_on_samples": 0,
            }
        
        placeholders = ",".join("?" * len(recent_turns))
        cursor = conn.execute(
            f"""
            SELECT 
                AVG(bid_amount) as avg_winning,
                MIN(bid_amount) as min_winning,
                MAX(bid_amount) as max_winning,
                COUNT(*) as samples
            FROM bid_history
            WHERE ingredient = ? AND won = 1 AND turn_id IN ({placeholders})
            """,
            [ingredient] + recent_turns,
        )
        row = cursor.fetchone()
        if row and row["samples"] and row["samples"] > 0:
            avg = row["avg_winning"]
            recommended = round(avg * 1.1, 2)
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


def get_recent_turns_with_bids(db_path: str | Path, window_size: int = DEFAULT_WINDOW_SIZE) -> list[int]:
    """Get the most recent N turn IDs that have bid_history data."""
    conn = get_connection(db_path)
    try:
        return _get_recent_turns(conn, window_size)
    finally:
        conn.close()
