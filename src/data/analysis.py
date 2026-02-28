"""Analysis tools and query helpers for market data."""
import csv
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class BidStats:
    """Statistics for bids on a specific ingredient."""
    ingredient: str
    total_bids: int
    wins: int
    losses: int
    win_rate: float
    avg_bid_price: float
    avg_winning_price: float | None
    min_winning_price: float | None
    max_winning_price: float | None


@dataclass
class DishProfitability:
    """Profitability analysis for a dish."""
    dish_name: str
    times_served: int
    total_revenue: float
    avg_price: float
    avg_cost: float | None
    avg_margin: float | None


@dataclass
class MarketOpportunity:
    """Identified market trading opportunity."""
    ingredient: str
    avg_buy_price: float
    avg_sell_price: float
    spread: float
    buy_volume: int
    sell_volume: int


class DataAnalyzer:
    """Query helper for market data analysis."""

    def __init__(self, db_path: str | Path = "data/market_data.db"):
        self.db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def get_winning_bid_stats(self, ingredient: str | None = None) -> list[BidStats]:
        """Get statistics on winning bids, optionally filtered by ingredient."""
        conn = self._get_conn()
        
        if ingredient:
            query = """
                SELECT 
                    ingredient,
                    COUNT(*) as total_bids,
                    SUM(CASE WHEN won = 1 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN won = 0 THEN 1 ELSE 0 END) as losses,
                    AVG(bid_price) as avg_bid_price,
                    AVG(CASE WHEN won = 1 THEN winning_price END) as avg_winning_price,
                    MIN(CASE WHEN won = 1 THEN winning_price END) as min_winning_price,
                    MAX(CASE WHEN won = 1 THEN winning_price END) as max_winning_price
                FROM bids
                WHERE ingredient = ?
                GROUP BY ingredient
            """
            rows = conn.execute(query, (ingredient,)).fetchall()
        else:
            query = """
                SELECT 
                    ingredient,
                    COUNT(*) as total_bids,
                    SUM(CASE WHEN won = 1 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN won = 0 THEN 1 ELSE 0 END) as losses,
                    AVG(bid_price) as avg_bid_price,
                    AVG(CASE WHEN won = 1 THEN winning_price END) as avg_winning_price,
                    MIN(CASE WHEN won = 1 THEN winning_price END) as min_winning_price,
                    MAX(CASE WHEN won = 1 THEN winning_price END) as max_winning_price
                FROM bids
                GROUP BY ingredient
                ORDER BY total_bids DESC
            """
            rows = conn.execute(query).fetchall()

        results = []
        for row in rows:
            total = row["total_bids"]
            wins = row["wins"] or 0
            results.append(BidStats(
                ingredient=row["ingredient"],
                total_bids=total,
                wins=wins,
                losses=row["losses"] or 0,
                win_rate=wins / total if total > 0 else 0,
                avg_bid_price=row["avg_bid_price"] or 0,
                avg_winning_price=row["avg_winning_price"],
                min_winning_price=row["min_winning_price"],
                max_winning_price=row["max_winning_price"],
            ))
        return results

    def get_recommended_bid_price(self, ingredient: str, percentile: float = 0.75) -> float | None:
        """Get recommended bid price based on historical winning prices."""
        conn = self._get_conn()
        query = """
            SELECT winning_price
            FROM bids
            WHERE ingredient = ? AND won = 1 AND winning_price IS NOT NULL
            ORDER BY winning_price
        """
        rows = conn.execute(query, (ingredient,)).fetchall()
        if not rows:
            return None
        
        prices = [row["winning_price"] for row in rows]
        idx = int(len(prices) * percentile)
        return prices[min(idx, len(prices) - 1)]

    def get_price_vs_cost_analysis(self) -> list[DishProfitability]:
        """Analyze dish profitability based on price vs ingredient cost."""
        conn = self._get_conn()
        query = """
            SELECT 
                m.dish_name,
                COUNT(DISTINCT o.id) as times_served,
                COALESCE(SUM(o.revenue), 0) as total_revenue,
                AVG(m.price) as avg_price,
                AVG(m.ingredients_cost) as avg_cost,
                AVG(m.profit_margin) as avg_margin
            FROM menu_items m
            LEFT JOIN orders o ON m.turn_id = o.turn_id AND m.dish_name = o.dish_served AND o.success = 1
            GROUP BY m.dish_name
            ORDER BY total_revenue DESC
        """
        rows = conn.execute(query).fetchall()
        
        return [
            DishProfitability(
                dish_name=row["dish_name"],
                times_served=row["times_served"] or 0,
                total_revenue=row["total_revenue"] or 0,
                avg_price=row["avg_price"] or 0,
                avg_cost=row["avg_cost"],
                avg_margin=row["avg_margin"],
            )
            for row in rows
        ]

    def get_market_opportunities(self) -> list[MarketOpportunity]:
        """Identify profitable market trading patterns."""
        conn = self._get_conn()
        query = """
            SELECT 
                ingredient,
                AVG(CASE WHEN side = 'BUY' THEN price END) as avg_buy_price,
                AVG(CASE WHEN side = 'SELL' THEN price END) as avg_sell_price,
                SUM(CASE WHEN side = 'BUY' THEN quantity ELSE 0 END) as buy_volume,
                SUM(CASE WHEN side = 'SELL' THEN quantity ELSE 0 END) as sell_volume
            FROM market_entries
            WHERE our_entry = 0
            GROUP BY ingredient
            HAVING avg_buy_price IS NOT NULL AND avg_sell_price IS NOT NULL
            ORDER BY (avg_buy_price - avg_sell_price) DESC
        """
        rows = conn.execute(query).fetchall()
        
        return [
            MarketOpportunity(
                ingredient=row["ingredient"],
                avg_buy_price=row["avg_buy_price"],
                avg_sell_price=row["avg_sell_price"],
                spread=row["avg_buy_price"] - row["avg_sell_price"],
                buy_volume=row["buy_volume"] or 0,
                sell_volume=row["sell_volume"] or 0,
            )
            for row in rows
        ]

    def get_turn_summary(self, turn_id: int) -> dict[str, Any]:
        """Get a summary of a specific turn."""
        conn = self._get_conn()
        
        turn = conn.execute("SELECT * FROM turns WHERE turn_id = ?", (turn_id,)).fetchone()
        if not turn:
            return {}
        
        bids = conn.execute(
            "SELECT COUNT(*) as total, SUM(CASE WHEN won = 1 THEN 1 ELSE 0 END) as won FROM bids WHERE turn_id = ?",
            (turn_id,)
        ).fetchone()
        
        orders = conn.execute(
            "SELECT COUNT(*) as total, SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful, SUM(revenue) as revenue FROM orders WHERE turn_id = ?",
            (turn_id,)
        ).fetchone()
        
        return {
            "turn_id": turn_id,
            "started_at": turn["started_at"],
            "ended_at": turn["ended_at"],
            "initial_balance": turn["initial_balance"],
            "final_balance": turn["final_balance"],
            "balance_change": (turn["final_balance"] or 0) - (turn["initial_balance"] or 0),
            "reputation_change": (turn["final_reputation"] or 0) - (turn["initial_reputation"] or 0),
            "bids_total": bids["total"] or 0,
            "bids_won": bids["won"] or 0,
            "orders_total": orders["total"] or 0,
            "orders_successful": orders["successful"] or 0,
            "revenue": orders["revenue"] or 0,
        }

    def get_all_turns_summary(self) -> list[dict[str, Any]]:
        """Get summary for all turns."""
        conn = self._get_conn()
        turn_ids = [row["turn_id"] for row in conn.execute("SELECT turn_id FROM turns ORDER BY turn_id").fetchall()]
        return [self.get_turn_summary(tid) for tid in turn_ids]

    def get_ingredient_demand(self) -> list[dict[str, Any]]:
        """Analyze ingredient demand based on bids and menu usage."""
        conn = self._get_conn()
        query = """
            SELECT 
                ingredient,
                COUNT(*) as bid_count,
                SUM(quantity) as total_quantity_bid,
                AVG(bid_price) as avg_bid_price
            FROM bids
            GROUP BY ingredient
            ORDER BY bid_count DESC
        """
        return [dict(row) for row in conn.execute(query).fetchall()]

    def export_to_csv(self, table: str, path: str | Path) -> int:
        """Export a table to CSV. Returns number of rows exported."""
        conn = self._get_conn()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        cursor = conn.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        
        if not rows:
            return 0
        
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(rows[0].keys())
            writer.writerows([tuple(row) for row in rows])
        
        return len(rows)

    def export_all_to_csv(self, output_dir: str | Path = "data/exports") -> dict[str, int]:
        """Export all tables to CSV files. Returns dict of table -> row count."""
        output_dir = Path(output_dir)
        tables = [
            "turns", "bids", "market_entries", "transactions", 
            "inventory_snapshots", "menu_items", "orders", "competitor_menus",
            "bid_history", "recipes", "restaurant_snapshots", "meals"
        ]
        
        results = {}
        for table in tables:
            try:
                count = self.export_to_csv(table, output_dir / f"{table}.csv")
                results[table] = count
            except Exception:
                results[table] = -1
        
        return results

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
