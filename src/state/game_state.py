"""Game state for Hackapizza restaurant. Updated from SSE events and HTTP endpoints."""
from dataclasses import dataclass, field
from typing import Any

import requests


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
    # Analyst output: suggested bid per unit for each ingredient. [(ingredient, price), ...]
    # Populated by the analyst (pre-bid → closed_bid). Broker uses these for bidding.
    suggested_bids: list[tuple[str, float]] = field(default_factory=list)
    # Broker output: actual auction results. [{ingredient, price, success}, ...]
    # Populated by the broker after closed_bid. Price = actual paid per unit; success = whether purchase went through.
    actual_bids: list[dict[str, Any]] = field(default_factory=list)
    # Target archetype from blog (Esploratore_Galattico, Astrobarone, Saggi_del_Cosmo, Famiglie_Orbitali).
    # Set by blog agent in speaking phase. None = use default (Astrobarone).
    # DEPRECATED: kept for backward compat; prefer blog_insight.
    target_archetype: str | None = None
    # Free-form strategic insight from the blog agent (e.g. "customers want fast cheap food").
    # Set by blog insight agent in speaking phase. None = no insight available.
    blog_insight: str | None = None
    # Draft selection mode: "blog_insight" (Case A) or "top_sold" (Case B).
    draft_selection_mode: str = "blog_insight"

    def summary(self) -> str:
        """Produce a concise context string for agents."""
        insight = self.blog_insight or "No blog insight available."
        parts = [
            f"Phase: {self.phase}",
            f"Turn: {self.turn_id}",
            f"Draft selection mode: {self.draft_selection_mode}",
            f"Blog insight: {insight}",
            f"Balance: {self.balance}",
            f"Reputation: {self.reputation}",
            f"Inventory: {self.inventory}",
            f"Menu: {self.menu}",
            f"Draft menu: {self.draft_menu}",
            #f"Recipes: {self.recipes}",
            f"Suggested bids (ingredient -> price/unit): {dict(self.suggested_bids) if self.suggested_bids else 'none'}",
            f"Actual bids (auction results): {self.actual_bids if self.actual_bids else 'none'}",
            f"Pending clients: {self.pending_clients}",
            f"Prepared dishes: {self.prepared_dishes}",
        ]
        return "\n".join(parts)

    def maitre_summary(self) -> str:
        """Produce a concise context string for agents."""
        insight = self.blog_insight or "No blog insight available."
        parts = [
            f"Phase: {self.phase}",
            f"Turn: {self.turn_id}",
            f"Menu: {self.menu}",
            f"Pending clients: {self.pending_clients}",
            f"Prepared dishes: {self.prepared_dishes}",
        ]
        return "\n".join(parts)


class StateUpdater:
    """Fetches and updates GameState from HTTP endpoints."""

    def __init__(self, base_url: str, api_key: str, restaurant_id: int):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.restaurant_id = restaurant_id
        self._headers = {"x-api-key": api_key}

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
        """Fetch all restaurants (for Diplomatico)."""
        state.restaurants = self._get("/restaurants") or []

    def refresh_meals(self, state: GameState) -> None:
        """Fetch meals for current turn."""
        if state.turn_id <= 0:
            return
        data = self._get("/meals", {"turn_id": state.turn_id, "restaurant_id": self.restaurant_id})
        state.meals = data if isinstance(data, list) else []

    def refresh_market(self, state: GameState) -> None:
        """Fetch market entries."""
        data = self._get("/market/entries")
        state.market_entries = data if isinstance(data, list) else []

    def sync_pending_clients(self, state: GameState) -> None:
        """Build pending_clients from meals (executed=false)."""
        pending = []
        for m in state.meals:
            if m.get("executed"):
                continue
            cid = str(m.get("customerId") or m.get("customer_id", ""))
            customer = m.get("customer", {})
            client_name = (
                customer.get("name", "") if isinstance(customer, dict)
                else m.get("clientName") or m.get("client_name", "")
            )
            order_text = m.get("request") or m.get("orderText") or m.get("order_text", "")
            pending.append(
                {
                    "client_id": cid,
                    "clientName": client_name,
                    "orderText": order_text,
                }
            )
        state.pending_clients = pending
