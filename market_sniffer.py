#!/usr/bin/env python3
"""
Market Sniffer - Standalone data collector for Hackapizza market intelligence.

Runs independently from the main game client, collecting:
- Market entries (BUY/SELL offers) from all restaurants
- SSE events (game phases, auctions, etc.)
- Restaurant states and menus
- Periodic snapshots for trend analysis

Usage:
    python market_sniffer.py                    # Run with default settings
    python market_sniffer.py --interval 5      # Poll every 5 seconds
    python market_sniffer.py --db custom.db    # Use custom database
    python market_sniffer.py --no-sse          # Only poll HTTP, no SSE stream
"""
import argparse
import asyncio
import json
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import aiohttp
import requests

from src.data import DataCollector


class MarketSniffer:
    """Standalone market data collector."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        team_id: int,
        db_path: str = "data/sniffer_data.db",
        poll_interval: int = 10,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.team_id = team_id
        self.poll_interval = poll_interval
        self._headers = {"x-api-key": api_key}
        self._collector = DataCollector(db_path)
        self._running = False
        self._current_turn = 0
        self._current_phase = "unknown"
        self._seen_entries: set[int] = set()
        self._poll_count = 0
        self._total_entries = 0
        self._total_bids = 0

    # ANSI colors + emoji per tag
    _TAG_STYLE: dict[str, tuple[str, str]] = {
        "SNIFFER":     ("\033[1;36m", "🔍"),  # bold cyan
        "TURN":        ("\033[1;33m", "🔄"),  # bold yellow
        "PHASE":       ("\033[1;35m", "⏱️"),   # bold magenta
        "POLL":        ("\033[0;37m", "📡"),   # gray
        "MARKET":      ("\033[0;32m", "📊"),   # green
        "AUCTION":     ("\033[0;33m", "🔨"),   # yellow
        "TRANSACTION": ("\033[0;32m", "💰"),   # green
        "SSE":         ("\033[0;34m", "📡"),   # blue
        "ERROR":       ("\033[1;31m", "❌"),   # bold red
    }
    _RESET = "\033[0m"

    def log(self, tag: str, message: str) -> None:
        color, emoji = self._TAG_STYLE.get(tag, ("\033[0m", "•"))
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"{color}{emoji} [{tag:>11}] {ts}{self._RESET}  {message}", flush=True)

    def _get(self, path: str, params: dict | None = None) -> dict | list | None:
        """HTTP GET request to game server."""
        try:
            url = f"{self.base_url}{path}"
            resp = requests.get(url, headers=self._headers, params=params or {}, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self.log("ERROR", f"GET {path} failed: {e}")
            return None

    def collect_market_entries(self) -> int:
        """Fetch and store all market entries. Returns count of new entries."""
        data = self._get("/market/entries")
        if not data or not isinstance(data, list):
            return 0

        new_count = 0
        for entry in data:
            entry_id = entry.get("id")
            if entry_id in self._seen_entries:
                continue

            self._seen_entries.add(entry_id)
            new_count += 1

            # Handle different API field names
            restaurant_id = (
                entry.get("createdByRestaurantId") 
                or entry.get("restaurant_id") 
                or entry.get("restaurantId")
            )
            
            # Ingredient can be a nested object or a string
            ingredient_data = entry.get("ingredient", {})
            if isinstance(ingredient_data, dict):
                ingredient_name = ingredient_data.get("name", "")
            else:
                ingredient_name = entry.get("ingredient_name") or entry.get("ingredientName", "")
            
            # Price can be totalPrice or price
            price = entry.get("totalPrice") or entry.get("price", 0)
            
            self._collector.record_market_entry(
                turn_id=self._current_turn,
                entry_id=entry_id,
                side=entry.get("side", ""),
                ingredient=ingredient_name,
                quantity=entry.get("quantity", 0),
                price=price,
                restaurant_id=restaurant_id,
                restaurant_name=entry.get("restaurant_name") or entry.get("restaurantName", ""),
                our_entry=(restaurant_id == self.team_id),
            )

        return new_count

    def collect_restaurants(self) -> None:
        """Fetch and store all restaurant states and menus."""
        data = self._get("/restaurants")
        if not data or not isinstance(data, list):
            return

        for restaurant in data:
            rid = restaurant.get("id")
            if not rid:
                continue
            
            # Convert rid to int for comparison
            try:
                rid_int = int(rid)
            except (ValueError, TypeError):
                rid_int = rid

            # Menu can be a dict with 'items' key or a list directly
            menu_data = restaurant.get("menu", {})
            if isinstance(menu_data, dict):
                menu_items = menu_data.get("items", [])
            elif isinstance(menu_data, list):
                menu_items = menu_data
            else:
                menu_items = []
            
            if menu_items and rid_int != self.team_id:
                self._collector.record_competitor_menu(
                    turn_id=self._current_turn,
                    restaurant_id=rid_int,
                    restaurant_name=restaurant.get("name", ""),
                    menu_items=menu_items,
                )
        
        # Also record full restaurant snapshots
        if self._current_turn > 0:
            self._collector.record_restaurants_snapshot(self._current_turn, data)

    def _probe_bid_history(self, turn_id: int) -> str:
        """Probe /bid_history for a turn. Returns 'valid', 'too_old', or 'error' (silent)."""
        try:
            url = f"{self.base_url}/bid_history"
            resp = requests.get(url, headers=self._headers, params={"turn_id": turn_id}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return "valid" if isinstance(data, list) else "error"
            # 400 = "too old" or bad request — parse body
            try:
                body = resp.json()
                if "too old" in body.get("message", ""):
                    return "too_old"
            except Exception:
                pass
            return "error"
        except Exception:
            return "error"

    def _detect_current_turn(self) -> None:
        """Detect the current turn by probing /bid_history.
        
        Uses binary search to find the highest valid turn_id.
        The API returns 400 'too old' for turns older than current-2,
        200 with a list for valid turns, and errors for future turns.
        """
        if self._current_turn == 0:
            # Binary search: find the boundary between "too_old" and "valid"/"error"
            lo, hi = 1, 100
            best = 0
            
            # First: check if turn 1 is too old (game has progressed)
            r = self._probe_bid_history(1)
            if r == "valid":
                best = 1
            elif r != "too_old":
                # Turn 1 is error → game hasn't started or no bid history at all
                return
            
            # Binary search for the transition point
            while lo <= hi:
                mid = (lo + hi) // 2
                r = self._probe_bid_history(mid)
                if r == "too_old":
                    lo = mid + 1
                elif r == "valid":
                    best = mid
                    lo = mid + 1  # Try higher
                else:
                    hi = mid - 1  # Error/future → go lower
            
            if best > 0:
                self._current_turn = best
                self.log("TURN", f"Detected current turn: {best}")
        else:
            # Already have a turn → just check if it advanced
            result = self._probe_bid_history(self._current_turn + 1)
            if result == "valid":
                self._current_turn += 1
                self._seen_entries.clear()
                self.log("TURN", f"Turn advanced to {self._current_turn}")

    def collect_own_state(self) -> dict[str, Any]:
        """Fetch our restaurant state."""
        data = self._get(f"/restaurant/{self.team_id}")
        if not data or not isinstance(data, dict):
            return {}

        if self._current_turn > 0:
            inventory = data.get("inventory", {})
            if inventory:
                self._collector.record_inventory_snapshot(
                    self._current_turn, self._current_phase, inventory
                )

        return data

    def collect_bid_history(self, turn_id: int | None = None) -> int:
        """Fetch and store bid history. Returns count of new records."""
        tid = turn_id or self._current_turn
        if tid <= 0:
            return 0
        
        data = self._get("/bid_history", {"turn_id": tid})
        if not data or not isinstance(data, list):
            return 0
        
        return self._collector.record_bid_history_batch(tid, data)

    def collect_recipes(self) -> int:
        """Fetch and store all recipes. Returns count of records."""
        data = self._get("/recipes")
        if not data or not isinstance(data, list):
            return 0
        
        return self._collector.record_recipes_batch(data)

    def collect_meals(self, turn_id: int | None = None) -> int:
        """Fetch and store meals for a turn. Returns count of records."""
        tid = turn_id or self._current_turn
        if tid <= 0:
            return 0
        
        data = self._get("/meals", {"turn_id": tid, "restaurant_id": self.team_id})
        if not data or not isinstance(data, list):
            return 0
        
        return self._collector.record_meals_batch(tid, self.team_id, data)

    async def handle_sse_event(self, event_type: str, event_data: dict[str, Any]) -> None:
        """Process SSE events for data collection."""
        if event_type == "game_started":
            self._current_turn = event_data.get("turn_id", 0)
            self._current_phase = "speaking"
            self._seen_entries.clear()

            state = self.collect_own_state()
            self._collector.record_turn_start(
                self._current_turn,
                state.get("balance", 0),
                state.get("reputation", 0),
            )
            self.log("TURN", f"Turn {self._current_turn} started")

        elif event_type == "game_phase_changed":
            self._current_phase = event_data.get("phase", "unknown")
            self.log("PHASE", f"Phase changed to {self._current_phase}")

            # Collect data on phase change
            self.collect_own_state()
            new_entries = self.collect_market_entries()
            if new_entries > 0:
                self.log("MARKET", f"Found {new_entries} new market entries")

            if self._current_phase == "stopped":
                state = self.collect_own_state()
                self._collector.record_turn_end(
                    self._current_turn,
                    state.get("balance", 0),
                    state.get("reputation", 0),
                )
                self.log("TURN", f"Turn {self._current_turn} ended")

        elif event_type == "auction_results":
            # Capture auction results if available
            results = event_data.get("results", [])
            for result in results:
                ingredient = result.get("ingredient", "")
                winner_id = result.get("winner_id") or result.get("winnerId")
                winning_price = result.get("winning_price") or result.get("winningPrice")
                quantity = result.get("quantity", 0)

                won = (winner_id == self.team_id)
                self._collector.update_bid_result(
                    self._current_turn,
                    ingredient,
                    won=won,
                    winning_price=winning_price,
                    quantity_won=quantity if won else 0,
                )
                self.log("AUCTION", f"{ingredient}: winner={winner_id} price={winning_price}")

        elif event_type == "market_entry_created":
            # New market entry appeared
            entry = event_data
            entry_id = entry.get("id") or entry.get("entry_id")
            if entry_id and entry_id not in self._seen_entries:
                self._seen_entries.add(entry_id)
                restaurant_id = entry.get("restaurant_id") or entry.get("restaurantId")
                self._collector.record_market_entry(
                    turn_id=self._current_turn,
                    entry_id=entry_id,
                    side=entry.get("side", ""),
                    ingredient=entry.get("ingredient_name") or entry.get("ingredientName", ""),
                    quantity=entry.get("quantity", 0),
                    price=entry.get("price", 0),
                    restaurant_id=restaurant_id,
                    restaurant_name=entry.get("restaurant_name") or entry.get("restaurantName", ""),
                    our_entry=(restaurant_id == self.team_id),
                )
                self.log("MARKET", f"New entry: {entry.get('side')} {entry.get('ingredient_name')}")

        elif event_type == "transaction_executed":
            # Market transaction completed
            self._collector.record_transaction(
                turn_id=self._current_turn,
                entry_id=event_data.get("entry_id"),
                ingredient=event_data.get("ingredient", ""),
                quantity=event_data.get("quantity", 0),
                price=event_data.get("price", 0),
                side=event_data.get("side", ""),
                counterparty_id=event_data.get("counterparty_id"),
                counterparty_name=event_data.get("counterparty_name"),
            )
            self.log("TRANSACTION", f"Executed: {event_data.get('ingredient')}")

    async def sse_listener(self) -> None:
        """Listen to SSE stream for real-time events."""
        url = f"{self.base_url}/events/{self.team_id}"
        headers = {"Accept": "text/event-stream", "x-api-key": self.api_key}
        timeout = aiohttp.ClientTimeout(total=None, sock_connect=15, sock_read=None)

        while self._running:
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, headers=headers) as response:
                        response.raise_for_status()
                        self.log("SSE", "Connected to event stream")

                        async for line in response.content:
                            if not self._running:
                                break
                            await self._process_sse_line(line)

            except asyncio.CancelledError:
                break
            except aiohttp.ClientResponseError as e:
                if e.status == 409:
                    self.log("SSE", "409 Conflict - Another SSE session is active (main client running?)")
                    self.log("SSE", "Tip: Use --no-sse flag to run alongside the main client.")
                    return  # Exit SSE listener, polling will continue
                self.log("SSE", f"Connection error: {e}, reconnecting in 5s...")
                await asyncio.sleep(5)
            except Exception as e:
                self.log("SSE", f"Connection error: {e}, reconnecting in 5s...")
                await asyncio.sleep(5)

    async def _process_sse_line(self, raw_line: bytes) -> None:
        """Parse and process a single SSE line."""
        if not raw_line:
            return

        line = raw_line.decode("utf-8", errors="ignore").strip()
        if not line:
            return

        if line.startswith("data:"):
            payload = line[5:].strip()
            if payload == "connected":
                return
            line = payload

        try:
            event_json = json.loads(line)
            event_type = event_json.get("type", "unknown")
            event_data = event_json.get("data", {})
            if not isinstance(event_data, dict):
                event_data = {"value": event_data}
            await self.handle_sse_event(event_type, event_data)
        except json.JSONDecodeError:
            pass

    async def polling_task(self) -> None:
        """Periodically poll HTTP endpoints for data."""
        while self._running:
            try:
                # Detect turn via bid_history probe (critical for --no-sse mode)
                if self._poll_count % 3 == 0:
                    self._detect_current_turn()

                new_entries = self.collect_market_entries()
                if new_entries > 0:
                    self._total_entries += new_entries
                    self.log("MARKET", f"+{new_entries} market entries (total: {self._total_entries})")

                # Collect restaurant data less frequently (every 3 polls)
                if self._poll_count % 3 == 0:
                    self.collect_restaurants()
                
                # Try to collect bid history if we have a turn
                new_bids = 0
                if self._current_turn > 0 and self._poll_count % 5 == 0:
                    try:
                        new_bids = self.collect_bid_history()
                        if new_bids > 0:
                            self._total_bids += new_bids
                            self.log("MARKET", f"+{new_bids} bids from history (total: {self._total_bids})")
                    except Exception:
                        pass

                # Periodic status summary (every 10 polls = ~100s)
                if self._poll_count > 0 and self._poll_count % 10 == 0:
                    self.log("SNIFFER",
                        f"status: turn={self._current_turn} phase={self._current_phase} "
                        f"entries={self._total_entries} bids={self._total_bids} "
                        f"polls={self._poll_count}")
                
                self._poll_count += 1

            except Exception as e:
                self.log("ERROR", f"Polling failed: {e}")

            await asyncio.sleep(self.poll_interval)

    async def run(self, use_sse: bool = True) -> None:
        """Run the sniffer."""
        self._running = True
        mode = "SSE + polling" if use_sse else "polling only"

        print(f"\n\033[1;36m{'═'*55}")
        print(f"  🍕 HACKAPIZZA MARKET SNIFFER")
        print(f"{'═'*55}\033[0m")
        print(f"  Team ID:    {self.team_id}")
        print(f"  Database:   {self._collector.db_path}")
        print(f"  Mode:       {mode}")
        print(f"  Interval:   {self.poll_interval}s")
        print(f"\033[1;36m{'═'*55}\033[0m\n", flush=True)

        # Initial data collection
        self.log("SNIFFER", "Collecting initial data...")
        recipe_count = self.collect_recipes()
        entry_count = self.collect_market_entries()
        self._total_entries = entry_count
        self.collect_restaurants()
        self.collect_own_state()
        self._detect_current_turn()

        self.log("SNIFFER",
            f"Ready! recipes={recipe_count} entries={entry_count} "
            f"turn={self._current_turn} — polling every {self.poll_interval}s")

        tasks = [asyncio.create_task(self.polling_task())]
        if use_sse:
            tasks.append(asyncio.create_task(self.sse_listener()))

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            pass
        finally:
            self._running = False
            self._collector.close()
            self.log("SNIFFER",
                f"Stopped. Total: entries={self._total_entries} bids={self._total_bids} "
                f"polls={self._poll_count}")

    def stop(self) -> None:
        """Signal the sniffer to stop."""
        self._running = False


def main():
    parser = argparse.ArgumentParser(
        description="Market Sniffer - Standalone data collector for Hackapizza",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python market_sniffer.py                    # Run with defaults
  python market_sniffer.py --interval 5      # Poll every 5 seconds
  python market_sniffer.py --db custom.db    # Use custom database
  python market_sniffer.py --no-sse          # HTTP polling only
        """,
    )
    parser.add_argument(
        "--db",
        default="data/sniffer_data.db",
        help="Path to SQLite database (default: data/sniffer_data.db)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=10,
        help="Polling interval in seconds (default: 10)",
    )
    parser.add_argument(
        "--no-sse",
        action="store_true",
        help="Disable SSE stream, use HTTP polling only (use this when main client is running)",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="Override base URL (default: from .env)",
    )
    parser.add_argument(
        "--team-id",
        type=int,
        default=None,
        help="Override team ID (default: from .env)",
    )

    args = parser.parse_args()

    # Load config
    from src.config import BASE_URL, TEAM_API_KEY, TEAM_ID

    base_url = args.base_url or BASE_URL
    team_id = args.team_id or TEAM_ID

    if not TEAM_API_KEY:
        print("Error: TEAM_API_KEY not set in .env")
        sys.exit(1)
    if team_id <= 0:
        print("Error: TEAM_ID not set or invalid")
        sys.exit(1)

    sniffer = MarketSniffer(
        base_url=base_url,
        api_key=TEAM_API_KEY,
        team_id=team_id,
        db_path=args.db,
        poll_interval=args.interval,
    )

    # Handle graceful shutdown
    def signal_handler(sig, frame):
        print("\nShutting down...")
        sniffer.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        asyncio.run(sniffer.run(use_sse=not args.no_sse))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
