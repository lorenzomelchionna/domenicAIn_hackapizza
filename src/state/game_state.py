"""Game state for Hackapizza restaurant. Updated from SSE events and HTTP endpoints."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

import requests

if TYPE_CHECKING:
    from src.data import DataCollector


@dataclass
class GameState:
    """Shared state for the multi-agent system."""

    phase: str = "stopped"
    turn_id: int = 0
    restaurant_id: int = 0
    balance: float = 0.0
    inventory: dict[str, int] = field(default_factory=dict)
    menu: list[dict[str, Any]] = field(default_factory=list)
    reputation: float = 0.0
    recipes: list[dict[str, Any]] = field(default_factory=list)
    restaurants: list[dict[str, Any]] = field(default_factory=list)
    meals: list[dict[str, Any]] = field(default_factory=list)
    market_entries: list[dict[str, Any]] = field(default_factory=list)
    pending_clients: list[dict[str, Any]] = field(default_factory=list)
    prepared_dishes: list[tuple[str, str]] = field(default_factory=list)  # (dish_name, client_id)
    draft_menu: list[dict[str, Any]] = field(default_factory=list)
    is_open: bool = True

    def summary(self) -> str:
        """Produce a concise context string for agents."""
        parts = [
            f"Phase: {self.phase}",
            f"Turn: {self.turn_id}",
            f"Balance: {self.balance}",
            f"Reputation: {self.reputation}",
            f"Inventory: {self.inventory}",
            f"Menu: {self.menu}",
            f"Draft menu: {self.draft_menu}",
            f"Recipes: {self.recipes[:10]}",
            f"Pending clients: {self.pending_clients}",
            f"Prepared dishes: {self.prepared_dishes}",
        ]
        return "\n".join(parts)


class StateUpdater:
    """Fetches and updates GameState from HTTP endpoints."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        restaurant_id: int,
        data_collector: DataCollector | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.restaurant_id = restaurant_id
        self._headers = {"x-api-key": api_key}
        self._data_collector = data_collector

    def _get(self, path: str, params: dict | None = None) -> dict | list:
        url = f"{self.base_url}{path}"
        resp = requests.get(url, headers=self._headers, params=params or {}, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def refresh_restaurant(self, state: GameState) -> None:
        """Fetch restaurant info and update state."""
        data = self._get(f"/restaurant/{self.restaurant_id}")
        state.balance = data.get("balance", 0)
        state.inventory = data.get("inventory", {}) or {}
        state.menu = data.get("menu", []) or []
        state.reputation = data.get("reputation", 0)
        state.is_open = data.get("is_open", True)

    def refresh_recipes(self, state: GameState) -> None:
        """Fetch recipes (cache at startup)."""
        state.recipes = self._get("/recipes") or []

    def refresh_restaurants(self, state: GameState) -> None:
        """Fetch all restaurants (for Diplomatico) and collect competitor data."""
        state.restaurants = self._get("/restaurants") or []
        
        # Collect competitor menus for data analysis
        if self._data_collector and state.turn_id > 0:
            for restaurant in state.restaurants:
                rid = restaurant.get("id")
                if rid and rid != self.restaurant_id:
                    menu = restaurant.get("menu", [])
                    if menu:
                        self._data_collector.record_competitor_menu(
                            turn_id=state.turn_id,
                            restaurant_id=rid,
                            restaurant_name=restaurant.get("name", ""),
                            menu_items=menu,
                        )

    def refresh_meals(self, state: GameState) -> None:
        """Fetch meals for current turn."""
        if state.turn_id <= 0:
            return
        data = self._get("/meals", {"turn_id": state.turn_id, "restaurant_id": self.restaurant_id})
        state.meals = data if isinstance(data, list) else []

    def refresh_market(self, state: GameState) -> None:
        """Fetch market entries and collect data."""
        data = self._get("/market/entries")
        state.market_entries = data if isinstance(data, list) else []
        
        # Collect market snapshot for data analysis
        if self._data_collector and state.turn_id > 0 and state.market_entries:
            self._data_collector.record_market_snapshot(
                turn_id=state.turn_id,
                entries=state.market_entries,
                our_restaurant_id=self.restaurant_id,
            )

    def sync_pending_clients(self, state: GameState) -> None:
        """Build pending_clients from meals (executed=false)."""
        pending = []
        for m in state.meals:
            if m.get("executed"):
                continue
            cid = str(m.get("customerId"))
            pending.append(
                {
                    "client_id": cid,
                    "clientName": m.get("clientName", ""),
                    "orderText": m.get("orderText", ""),
                }
            )
        state.pending_clients = pending
