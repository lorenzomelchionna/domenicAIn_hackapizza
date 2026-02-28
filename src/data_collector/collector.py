"""DataCollector class for collecting game data from Hackapizza API."""
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from .db import get_connection, init_db


class DataCollector:
    """Collects and persists game data from Hackapizza API to SQLite."""

    def __init__(self, base_url: str, api_key: str, db_path: str | Path, restaurant_id: int):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.db_path = Path(db_path)
        self.restaurant_id = restaurant_id
        self._headers = {"x-api-key": api_key}
        
        init_db(self.db_path)

    def _get(self, path: str, params: dict | None = None) -> dict | list | None:
        """Make GET request to API."""
        url = f"{self.base_url}{path}"
        try:
            resp = requests.get(url, headers=self._headers, params=params or {}, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"[DATA_COLLECTOR] GET {path} failed: {e}")
            return None

    def collect_bid_history(self, turn_id: int) -> int:
        """Collect bid history for a turn. Returns number of records inserted."""
        data = self._get("/bid_history", {"turn_id": turn_id})
        if not data or not isinstance(data, list):
            return 0

        conn = get_connection(self.db_path)
        inserted = 0
        try:
            cursor = conn.cursor()
            for bid in data:
                cursor.execute(
                    """
                    INSERT INTO bid_history (turn_id, restaurant_id, ingredient, bid_amount, quantity, won)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        turn_id,
                        bid.get("restaurant_id") or bid.get("restaurantId"),
                        bid.get("ingredient") or bid.get("ingredientName"),
                        bid.get("bid") or bid.get("bid_amount") or bid.get("bidAmount", 0),
                        bid.get("quantity", 0),
                        bid.get("won"),
                    ),
                )
                inserted += 1
            conn.commit()
        finally:
            conn.close()
        return inserted

    def collect_meals(self, turn_id: int, restaurant_id: int | None = None) -> int:
        """Collect meals for a turn. If restaurant_id is None, collects for all restaurants."""
        params: dict[str, Any] = {"turn_id": turn_id}
        if restaurant_id is not None:
            params["restaurant_id"] = restaurant_id

        data = self._get("/meals", params)
        if not data or not isinstance(data, list):
            return 0

        conn = get_connection(self.db_path)
        inserted = 0
        try:
            cursor = conn.cursor()
            for meal in data:
                rid = meal.get("restaurant_id") or meal.get("restaurantId") or restaurant_id or 0
                cursor.execute(
                    """
                    INSERT INTO meals (turn_id, restaurant_id, customer_id, client_name, dish_name, price, executed, order_text)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        turn_id,
                        rid,
                        str(meal.get("customerId") or meal.get("customer_id", "")),
                        meal.get("clientName") or meal.get("client_name", ""),
                        meal.get("dishName") or meal.get("dish_name", ""),
                        meal.get("price"),
                        meal.get("executed"),
                        meal.get("orderText") or meal.get("order_text", ""),
                    ),
                )
                inserted += 1
            conn.commit()
        finally:
            conn.close()
        return inserted

    def collect_market_entries(self, turn_id: int) -> int:
        """Collect current market entries. Returns number of records inserted."""
        data = self._get("/market/entries")
        if not data or not isinstance(data, list):
            return 0

        conn = get_connection(self.db_path)
        inserted = 0
        try:
            cursor = conn.cursor()
            for entry in data:
                entry_id = entry.get("id") or entry.get("entry_id") or entry.get("entryId", 0)
                cursor.execute(
                    """
                    INSERT INTO market_entries (entry_id, turn_id, restaurant_id, side, ingredient_name, quantity, price, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entry_id,
                        turn_id,
                        entry.get("restaurant_id") or entry.get("restaurantId", 0),
                        entry.get("side", ""),
                        entry.get("ingredient_name") or entry.get("ingredientName", ""),
                        entry.get("quantity", 0),
                        entry.get("price", 0),
                        entry.get("is_active", True) if "is_active" in entry else True,
                    ),
                )
                inserted += 1
            conn.commit()
        finally:
            conn.close()
        return inserted

    def collect_restaurants(self, turn_id: int) -> int:
        """Collect snapshot of all restaurants. Returns number of records inserted."""
        data = self._get("/restaurants")
        if not data or not isinstance(data, list):
            return 0

        conn = get_connection(self.db_path)
        inserted = 0
        try:
            cursor = conn.cursor()
            for restaurant in data:
                rid = restaurant.get("id") or restaurant.get("restaurant_id") or restaurant.get("restaurantId", 0)
                menu = restaurant.get("menu")
                menu_json = json.dumps(menu, ensure_ascii=False) if menu else None
                inventory = restaurant.get("inventory")
                inventory_json = json.dumps(inventory, ensure_ascii=False) if inventory else None
                
                cursor.execute(
                    """
                    INSERT INTO restaurant_snapshots (turn_id, restaurant_id, name, balance, reputation, is_open, menu_json, inventory_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        turn_id,
                        rid,
                        restaurant.get("name", ""),
                        restaurant.get("balance"),
                        restaurant.get("reputation"),
                        restaurant.get("is_open") or restaurant.get("isOpen"),
                        menu_json,
                        inventory_json,
                    ),
                )
                inserted += 1
            conn.commit()
        finally:
            conn.close()
        return inserted

    def collect_own_restaurant(self, turn_id: int) -> int:
        """Collect snapshot of own restaurant. Returns 1 if successful, 0 otherwise."""
        data = self._get(f"/restaurant/{self.restaurant_id}")
        if not data or not isinstance(data, dict):
            return 0

        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            menu = data.get("menu")
            menu_json = json.dumps(menu, ensure_ascii=False) if menu else None
            inventory = data.get("inventory")
            inventory_json = json.dumps(inventory, ensure_ascii=False) if inventory else None
            
            cursor.execute(
                """
                INSERT INTO restaurant_snapshots (turn_id, restaurant_id, name, balance, reputation, is_open, menu_json, inventory_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    turn_id,
                    self.restaurant_id,
                    data.get("name", ""),
                    data.get("balance"),
                    data.get("reputation"),
                    data.get("is_open") or data.get("isOpen"),
                    menu_json,
                    inventory_json,
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return 1

    def log_sse_event(self, turn_id: int | None, event_type: str, event_data: dict[str, Any] | None) -> None:
        """Log an SSE event to the database."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            data_json = json.dumps(event_data, ensure_ascii=False) if event_data else None
            cursor.execute(
                """
                INSERT INTO sse_events (turn_id, event_type, event_data)
                VALUES (?, ?, ?)
                """,
                (turn_id, event_type, data_json),
            )
            conn.commit()
        finally:
            conn.close()

    def collect_all_for_turn(self, turn_id: int) -> dict[str, int]:
        """Collect all available data for a turn. Returns counts of inserted records."""
        return {
            "bid_history": self.collect_bid_history(turn_id),
            "meals": self.collect_meals(turn_id, self.restaurant_id),
            "market_entries": self.collect_market_entries(turn_id),
            "restaurants": self.collect_restaurants(turn_id),
            "own_restaurant": self.collect_own_restaurant(turn_id),
        }
