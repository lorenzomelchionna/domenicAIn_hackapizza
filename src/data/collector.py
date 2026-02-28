"""SQLite-based data collector for market analytics."""
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


class DataCollector:
    """Collects and stores market data in SQLite for analysis."""

    def __init__(self, db_path: str | Path = "data/market_data.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._init_schema()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_schema(self) -> None:
        """Initialize database schema."""
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS turns (
                turn_id INTEGER PRIMARY KEY,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                initial_balance REAL,
                final_balance REAL,
                initial_reputation REAL,
                final_reputation REAL
            );

            CREATE TABLE IF NOT EXISTS bids (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                turn_id INTEGER NOT NULL,
                ingredient TEXT NOT NULL,
                bid_price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                won INTEGER,
                winning_price REAL,
                quantity_won INTEGER,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (turn_id) REFERENCES turns(turn_id)
            );

            CREATE TABLE IF NOT EXISTS market_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                turn_id INTEGER NOT NULL,
                entry_id INTEGER,
                side TEXT NOT NULL,
                ingredient TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                restaurant_id INTEGER,
                restaurant_name TEXT,
                our_entry INTEGER NOT NULL DEFAULT 0,
                executed INTEGER NOT NULL DEFAULT 0,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (turn_id) REFERENCES turns(turn_id)
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                turn_id INTEGER NOT NULL,
                entry_id INTEGER,
                ingredient TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                side TEXT NOT NULL,
                counterparty_id INTEGER,
                counterparty_name TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (turn_id) REFERENCES turns(turn_id)
            );

            CREATE TABLE IF NOT EXISTS inventory_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                turn_id INTEGER NOT NULL,
                phase TEXT NOT NULL,
                ingredient TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (turn_id) REFERENCES turns(turn_id)
            );

            CREATE TABLE IF NOT EXISTS menu_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                turn_id INTEGER NOT NULL,
                dish_name TEXT NOT NULL,
                price REAL NOT NULL,
                ingredients_cost REAL,
                profit_margin REAL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (turn_id) REFERENCES turns(turn_id)
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                turn_id INTEGER NOT NULL,
                client_id TEXT NOT NULL,
                client_name TEXT,
                dish_ordered TEXT,
                dish_served TEXT,
                success INTEGER,
                revenue REAL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (turn_id) REFERENCES turns(turn_id)
            );

            CREATE TABLE IF NOT EXISTS competitor_menus (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                turn_id INTEGER NOT NULL,
                restaurant_id INTEGER NOT NULL,
                restaurant_name TEXT,
                dish_name TEXT NOT NULL,
                price REAL NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (turn_id) REFERENCES turns(turn_id)
            );

            CREATE TABLE IF NOT EXISTS bid_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                turn_id INTEGER NOT NULL,
                restaurant_id INTEGER NOT NULL,
                restaurant_name TEXT,
                ingredient TEXT NOT NULL,
                ingredient_id INTEGER,
                bid_price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                won INTEGER,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                preparation_time_ms INTEGER,
                prestige INTEGER,
                ingredients_json TEXT,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS restaurant_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                turn_id INTEGER NOT NULL,
                restaurant_id INTEGER NOT NULL,
                restaurant_name TEXT,
                balance REAL,
                reputation REAL,
                is_open INTEGER,
                inventory_json TEXT,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS meals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                turn_id INTEGER NOT NULL,
                meal_id INTEGER,
                restaurant_id INTEGER NOT NULL,
                customer_id TEXT,
                customer_name TEXT,
                order_text TEXT,
                dish_served TEXT,
                executed INTEGER,
                timestamp TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_bids_turn ON bids(turn_id);
            CREATE INDEX IF NOT EXISTS idx_bids_ingredient ON bids(ingredient);
            CREATE INDEX IF NOT EXISTS idx_market_entries_turn ON market_entries(turn_id);
            CREATE INDEX IF NOT EXISTS idx_inventory_turn_phase ON inventory_snapshots(turn_id, phase);
            CREATE INDEX IF NOT EXISTS idx_orders_turn ON orders(turn_id);
            CREATE INDEX IF NOT EXISTS idx_bid_history_turn ON bid_history(turn_id);
            CREATE INDEX IF NOT EXISTS idx_bid_history_ingredient ON bid_history(ingredient);
            CREATE INDEX IF NOT EXISTS idx_restaurant_snapshots_turn ON restaurant_snapshots(turn_id);
            CREATE INDEX IF NOT EXISTS idx_meals_turn ON meals(turn_id);
        """)
        conn.commit()

    def _now(self) -> str:
        return datetime.now().isoformat()

    def record_turn_start(self, turn_id: int, balance: float, reputation: float) -> None:
        """Record the start of a new turn."""
        conn = self._get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO turns (turn_id, started_at, initial_balance, initial_reputation)
               VALUES (?, ?, ?, ?)""",
            (turn_id, self._now(), balance, reputation),
        )
        conn.commit()

    def record_turn_end(self, turn_id: int, balance: float, reputation: float) -> None:
        """Record the end of a turn."""
        conn = self._get_conn()
        conn.execute(
            """UPDATE turns SET ended_at = ?, final_balance = ?, final_reputation = ?
               WHERE turn_id = ?""",
            (self._now(), balance, reputation, turn_id),
        )
        conn.commit()

    def record_bid(
        self,
        turn_id: int,
        ingredient: str,
        bid_price: float,
        quantity: int,
        won: bool | None = None,
        winning_price: float | None = None,
        quantity_won: int | None = None,
    ) -> int:
        """Record a bid submission. Returns the bid record id."""
        conn = self._get_conn()
        cursor = conn.execute(
            """INSERT INTO bids (turn_id, ingredient, bid_price, quantity, won, winning_price, quantity_won, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (turn_id, ingredient, bid_price, quantity, won, winning_price, quantity_won, self._now()),
        )
        conn.commit()
        return cursor.lastrowid or 0

    def update_bid_result(
        self,
        turn_id: int,
        ingredient: str,
        won: bool,
        winning_price: float | None = None,
        quantity_won: int | None = None,
    ) -> None:
        """Update bid result after auction completes."""
        conn = self._get_conn()
        conn.execute(
            """UPDATE bids SET won = ?, winning_price = ?, quantity_won = ?
               WHERE turn_id = ? AND ingredient = ? AND won IS NULL""",
            (won, winning_price, quantity_won, turn_id, ingredient),
        )
        conn.commit()

    def record_market_entry(
        self,
        turn_id: int,
        entry_id: int | None,
        side: str,
        ingredient: str,
        quantity: int,
        price: float,
        restaurant_id: int | None = None,
        restaurant_name: str | None = None,
        our_entry: bool = False,
    ) -> int:
        """Record a market entry (BUY/SELL offer)."""
        conn = self._get_conn()
        cursor = conn.execute(
            """INSERT INTO market_entries 
               (turn_id, entry_id, side, ingredient, quantity, price, restaurant_id, restaurant_name, our_entry, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (turn_id, entry_id, side, ingredient, quantity, price, restaurant_id, restaurant_name, our_entry, self._now()),
        )
        conn.commit()
        return cursor.lastrowid or 0

    def record_market_snapshot(self, turn_id: int, entries: list[dict[str, Any]], our_restaurant_id: int) -> None:
        """Record a snapshot of all market entries."""
        conn = self._get_conn()
        timestamp = self._now()
        for entry in entries:
            entry_id = entry.get("id")
            existing = conn.execute(
                "SELECT id FROM market_entries WHERE turn_id = ? AND entry_id = ?",
                (turn_id, entry_id),
            ).fetchone()
            if existing:
                continue
            restaurant_id = entry.get("restaurant_id") or entry.get("restaurantId")
            conn.execute(
                """INSERT INTO market_entries 
                   (turn_id, entry_id, side, ingredient, quantity, price, restaurant_id, restaurant_name, our_entry, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    turn_id,
                    entry_id,
                    entry.get("side", ""),
                    entry.get("ingredient_name") or entry.get("ingredientName", ""),
                    entry.get("quantity", 0),
                    entry.get("price", 0),
                    restaurant_id,
                    entry.get("restaurant_name") or entry.get("restaurantName", ""),
                    1 if restaurant_id == our_restaurant_id else 0,
                    timestamp,
                ),
            )
        conn.commit()

    def mark_market_entry_executed(self, turn_id: int, entry_id: int) -> None:
        """Mark a market entry as executed."""
        conn = self._get_conn()
        conn.execute(
            "UPDATE market_entries SET executed = 1 WHERE turn_id = ? AND entry_id = ?",
            (turn_id, entry_id),
        )
        conn.commit()

    def record_transaction(
        self,
        turn_id: int,
        entry_id: int | None,
        ingredient: str,
        quantity: int,
        price: float,
        side: str,
        counterparty_id: int | None = None,
        counterparty_name: str | None = None,
    ) -> int:
        """Record a completed transaction."""
        conn = self._get_conn()
        cursor = conn.execute(
            """INSERT INTO transactions 
               (turn_id, entry_id, ingredient, quantity, price, side, counterparty_id, counterparty_name, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (turn_id, entry_id, ingredient, quantity, price, side, counterparty_id, counterparty_name, self._now()),
        )
        conn.commit()
        return cursor.lastrowid or 0

    def record_inventory_snapshot(self, turn_id: int, phase: str, inventory: dict[str, int]) -> None:
        """Record inventory state at a given phase."""
        conn = self._get_conn()
        timestamp = self._now()
        for ingredient, quantity in inventory.items():
            conn.execute(
                """INSERT INTO inventory_snapshots (turn_id, phase, ingredient, quantity, timestamp)
                   VALUES (?, ?, ?, ?, ?)""",
                (turn_id, phase, ingredient, quantity, timestamp),
            )
        conn.commit()

    def record_menu_item(
        self,
        turn_id: int,
        dish_name: str,
        price: float,
        ingredients_cost: float | None = None,
        profit_margin: float | None = None,
    ) -> int:
        """Record a menu item."""
        conn = self._get_conn()
        cursor = conn.execute(
            """INSERT INTO menu_items (turn_id, dish_name, price, ingredients_cost, profit_margin, timestamp)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (turn_id, dish_name, price, ingredients_cost, profit_margin, self._now()),
        )
        conn.commit()
        return cursor.lastrowid or 0

    def record_menu(self, turn_id: int, menu_items: list[dict[str, Any]]) -> None:
        """Record the full menu for a turn."""
        for item in menu_items:
            self.record_menu_item(
                turn_id,
                item.get("name", ""),
                item.get("price", 0),
                item.get("ingredients_cost"),
                item.get("profit_margin"),
            )

    def record_order(
        self,
        turn_id: int,
        client_id: str,
        client_name: str | None = None,
        dish_ordered: str | None = None,
        dish_served: str | None = None,
        success: bool | None = None,
        revenue: float | None = None,
    ) -> int:
        """Record a client order."""
        conn = self._get_conn()
        cursor = conn.execute(
            """INSERT INTO orders (turn_id, client_id, client_name, dish_ordered, dish_served, success, revenue, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (turn_id, client_id, client_name, dish_ordered, dish_served, success, revenue, self._now()),
        )
        conn.commit()
        return cursor.lastrowid or 0

    def update_order_served(
        self,
        turn_id: int,
        client_id: str,
        dish_served: str,
        success: bool,
        revenue: float | None = None,
    ) -> None:
        """Update an order when dish is served."""
        conn = self._get_conn()
        conn.execute(
            """UPDATE orders SET dish_served = ?, success = ?, revenue = ?
               WHERE turn_id = ? AND client_id = ? AND dish_served IS NULL""",
            (dish_served, success, revenue, turn_id, client_id),
        )
        conn.commit()

    def record_competitor_menu(
        self,
        turn_id: int,
        restaurant_id: int,
        restaurant_name: str | None,
        menu_items: list[dict[str, Any] | str],
    ) -> None:
        """Record a competitor's menu. Handles both dict and string formats.
        
        Replaces any existing menu for the same turn/restaurant to avoid duplicates.
        """
        conn = self._get_conn()
        timestamp = self._now()
        # Remove old entries for this turn/restaurant to avoid duplicates from repeated polling
        conn.execute(
            "DELETE FROM competitor_menus WHERE turn_id = ? AND restaurant_id = ?",
            (turn_id, restaurant_id),
        )
        for item in menu_items:
            if isinstance(item, str):
                dish_name = item
                price = 0
            elif isinstance(item, dict):
                dish_name = item.get("name", "")
                price = item.get("price", 0)
            else:
                continue
            conn.execute(
                """INSERT INTO competitor_menus (turn_id, restaurant_id, restaurant_name, dish_name, price, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (turn_id, restaurant_id, restaurant_name, dish_name, price, timestamp),
            )
        conn.commit()

    def record_bid_history(
        self,
        turn_id: int,
        restaurant_id: int,
        restaurant_name: str | None,
        ingredient: str,
        ingredient_id: int | None,
        bid_price: float,
        quantity: int,
        won: bool | None = None,
    ) -> int:
        """Record a bid from the bid history endpoint."""
        conn = self._get_conn()
        cursor = conn.execute(
            """INSERT INTO bid_history 
               (turn_id, restaurant_id, restaurant_name, ingredient, ingredient_id, bid_price, quantity, won, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (turn_id, restaurant_id, restaurant_name, ingredient, ingredient_id, bid_price, quantity, won, self._now()),
        )
        conn.commit()
        return cursor.lastrowid or 0

    def record_bid_history_batch(self, turn_id: int, bids: list[dict[str, Any]]) -> int:
        """Record multiple bids from bid_history endpoint. Returns count of new records.
        
        Skips bids already recorded for this turn/restaurant/ingredient to avoid duplicates.
        """
        conn = self._get_conn()
        timestamp = self._now()
        count = 0
        for bid in bids:
            ingredient_data = bid.get("ingredient", {})
            if isinstance(ingredient_data, dict):
                ingredient_name = ingredient_data.get("name", "")
                ingredient_id = ingredient_data.get("id")
            else:
                ingredient_name = bid.get("ingredientName", "")
                ingredient_id = bid.get("ingredientId")
            
            restaurant_id = bid.get("restaurantId") or bid.get("restaurant_id")
            bid_price = bid.get("bid") or bid.get("bidPrice", 0)
            quantity = bid.get("quantity", 0)
            
            # Skip if already recorded
            existing = conn.execute(
                """SELECT id FROM bid_history 
                   WHERE turn_id = ? AND restaurant_id = ? AND ingredient = ? AND bid_price = ? AND quantity = ?""",
                (turn_id, restaurant_id, ingredient_name, bid_price, quantity),
            ).fetchone()
            if existing:
                continue
            
            conn.execute(
                """INSERT INTO bid_history 
                   (turn_id, restaurant_id, restaurant_name, ingredient, ingredient_id, bid_price, quantity, won, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    turn_id,
                    restaurant_id,
                    bid.get("restaurantName") or bid.get("restaurant_name", ""),
                    ingredient_name,
                    ingredient_id,
                    bid_price,
                    quantity,
                    bid.get("won"),
                    timestamp,
                ),
            )
            count += 1
        conn.commit()
        return count

    def record_recipe(
        self,
        name: str,
        preparation_time_ms: int | None,
        prestige: int | None,
        ingredients: dict[str, int] | None,
    ) -> None:
        """Record a recipe. Updates if already exists."""
        conn = self._get_conn()
        ingredients_json = json.dumps(ingredients) if ingredients else None
        conn.execute(
            """INSERT OR REPLACE INTO recipes (name, preparation_time_ms, prestige, ingredients_json, timestamp)
               VALUES (?, ?, ?, ?, ?)""",
            (name, preparation_time_ms, prestige, ingredients_json, self._now()),
        )
        conn.commit()

    def record_recipes_batch(self, recipes: list[dict[str, Any]]) -> int:
        """Record multiple recipes. Returns count of records."""
        conn = self._get_conn()
        timestamp = self._now()
        count = 0
        for recipe in recipes:
            ingredients = recipe.get("ingredients", {})
            ingredients_json = json.dumps(ingredients) if ingredients else None
            conn.execute(
                """INSERT OR REPLACE INTO recipes (name, preparation_time_ms, prestige, ingredients_json, timestamp)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    recipe.get("name", ""),
                    recipe.get("preparationTimeMs"),
                    recipe.get("prestige"),
                    ingredients_json,
                    timestamp,
                ),
            )
            count += 1
        conn.commit()
        return count

    def record_restaurant_snapshot(
        self,
        turn_id: int,
        restaurant_id: int,
        restaurant_name: str | None,
        balance: float | None,
        reputation: float | None,
        is_open: bool | None,
        inventory: dict[str, int] | None,
    ) -> int:
        """Record a snapshot of a restaurant's state."""
        conn = self._get_conn()
        inventory_json = json.dumps(inventory) if inventory else None
        cursor = conn.execute(
            """INSERT INTO restaurant_snapshots 
               (turn_id, restaurant_id, restaurant_name, balance, reputation, is_open, inventory_json, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (turn_id, restaurant_id, restaurant_name, balance, reputation, is_open, inventory_json, self._now()),
        )
        conn.commit()
        return cursor.lastrowid or 0

    def record_restaurants_snapshot(self, turn_id: int, restaurants: list[dict[str, Any]]) -> int:
        """Record snapshots of all restaurants. Returns count of records."""
        conn = self._get_conn()
        timestamp = self._now()
        count = 0
        for r in restaurants:
            rid = r.get("id")
            try:
                rid = int(rid)
            except (ValueError, TypeError):
                pass
            
            inventory = r.get("inventory", {})
            inventory_json = json.dumps(inventory) if inventory else None
            
            conn.execute(
                """INSERT INTO restaurant_snapshots 
                   (turn_id, restaurant_id, restaurant_name, balance, reputation, is_open, inventory_json, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    turn_id,
                    rid,
                    r.get("name", ""),
                    r.get("balance"),
                    r.get("reputation"),
                    r.get("isOpen"),
                    inventory_json,
                    timestamp,
                ),
            )
            count += 1
        conn.commit()
        return count

    def record_meal(
        self,
        turn_id: int,
        meal_id: int | None,
        restaurant_id: int,
        customer_id: str | None,
        customer_name: str | None,
        order_text: str | None,
        dish_served: str | None,
        executed: bool | None,
    ) -> int:
        """Record a meal from the meals endpoint."""
        conn = self._get_conn()
        cursor = conn.execute(
            """INSERT INTO meals 
               (turn_id, meal_id, restaurant_id, customer_id, customer_name, order_text, dish_served, executed, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (turn_id, meal_id, restaurant_id, customer_id, customer_name, order_text, dish_served, executed, self._now()),
        )
        conn.commit()
        return cursor.lastrowid or 0

    def record_meals_batch(self, turn_id: int, restaurant_id: int, meals: list[dict[str, Any]]) -> int:
        """Record multiple meals. Returns count of records."""
        conn = self._get_conn()
        timestamp = self._now()
        count = 0
        for meal in meals:
            conn.execute(
                """INSERT INTO meals 
                   (turn_id, meal_id, restaurant_id, customer_id, customer_name, order_text, dish_served, executed, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    turn_id,
                    meal.get("id"),
                    restaurant_id,
                    str(meal.get("customerId", "")),
                    meal.get("clientName") or meal.get("customerName", ""),
                    meal.get("orderText", ""),
                    meal.get("dishServed") or meal.get("dish_served"),
                    meal.get("executed"),
                    timestamp,
                ),
            )
            count += 1
        conn.commit()
        return count

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
