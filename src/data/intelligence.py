"""Market Intelligence - provides data-driven context for agent decision making."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .analysis import DataAnalyzer


@dataclass
class BiddingContext:
    """Context for auction bidding decisions."""
    suggested_prices: dict[str, float] = field(default_factory=dict)
    hot_ingredients: list[str] = field(default_factory=list)
    competitor_budgets: dict[str, float] = field(default_factory=dict)
    price_ranges: dict[str, dict[str, float]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "suggested_prices": self.suggested_prices,
            "hot_ingredients": self.hot_ingredients,
            "competitor_budgets": self.competitor_budgets,
            "price_ranges": self.price_ranges,
        }

    def to_prompt_string(self) -> str:
        """Format for injection into agent prompts."""
        lines = ["## MARKET INTELLIGENCE"]
        
        if self.suggested_prices:
            lines.append("\nSuggested bid prices (75th percentile of recent winning bids):")
            for ing, price in sorted(self.suggested_prices.items()):
                lines.append(f"  - {ing}: {price:.1f}")
        
        if self.hot_ingredients:
            lines.append(f"\nHot ingredients (high competition): {', '.join(self.hot_ingredients)}")
        
        if self.competitor_budgets:
            lines.append("\nCompetitor budgets:")
            for name, balance in sorted(self.competitor_budgets.items(), key=lambda x: -x[1]):
                lines.append(f"  - {name}: {balance:.0f}")
        
        if self.price_ranges:
            lines.append("\nPrice ranges (min-avg-max winning bids):")
            for ing, pr in sorted(self.price_ranges.items()):
                lines.append(f"  - {ing}: {pr.get('min', 0):.1f} - {pr.get('avg', 0):.1f} - {pr.get('max', 0):.1f}")
        
        return "\n".join(lines)


@dataclass
class TradingContext:
    """Context for market trading decisions."""
    spreads: list[dict[str, Any]] = field(default_factory=list)
    arbitrage_opportunities: list[dict[str, Any]] = field(default_factory=list)
    high_demand_ingredients: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "spreads": self.spreads,
            "arbitrage_opportunities": self.arbitrage_opportunities,
            "high_demand_ingredients": self.high_demand_ingredients,
        }

    def to_prompt_string(self) -> str:
        """Format for injection into agent prompts."""
        lines = ["## TRADING INTELLIGENCE"]
        
        if self.arbitrage_opportunities:
            lines.append("\nArbitrage opportunities (buy low, sell high):")
            for opp in self.arbitrage_opportunities:
                lines.append(
                    f"  - {opp['ingredient']}: BUY at {opp.get('best_buy_price', 'N/A')}, "
                    f"SELL at {opp.get('best_sell_price', 'N/A')}"
                )
        
        if self.high_demand_ingredients:
            lines.append(f"\nHigh demand (consider selling): {', '.join(self.high_demand_ingredients)}")
        
        if self.spreads:
            lines.append("\nCurrent market spreads:")
            for s in self.spreads[:10]:
                spread_str = f"{s.get('spread', 0):.1f}" if s.get('spread') is not None else "N/A"
                lines.append(
                    f"  - {s['ingredient']}: sell@{s.get('best_sell_price', 'N/A')} "
                    f"buy@{s.get('best_buy_price', 'N/A')} (spread: {spread_str})"
                )
        
        return "\n".join(lines)


@dataclass
class PricingContext:
    """Context for menu pricing decisions."""
    ingredient_costs: dict[str, float] = field(default_factory=dict)
    competitor_dish_prices: dict[str, list[float]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ingredient_costs": self.ingredient_costs,
            "competitor_dish_prices": self.competitor_dish_prices,
        }

    def to_prompt_string(self) -> str:
        """Format for injection into agent prompts."""
        lines = ["## PRICING INTELLIGENCE"]
        
        if self.ingredient_costs:
            lines.append("\nEstimated ingredient costs (based on recent auctions):")
            for ing, cost in sorted(self.ingredient_costs.items()):
                lines.append(f"  - {ing}: {cost:.1f} per unit")
        
        if self.competitor_dish_prices:
            lines.append("\nCompetitor dish prices:")
            for dish, prices in sorted(self.competitor_dish_prices.items()):
                if not prices:
                    continue
                avg_price = sum(prices) / len(prices)
                lines.append(f"  - {dish}: avg {avg_price:.1f} (range: {min(prices):.0f}-{max(prices):.0f})")
        
        return "\n".join(lines)


class MarketIntelligence:
    """Provides data-driven context for agent decision making.
    
    Uses recent data (configurable time window) to avoid stale information
    from early game turns affecting current decisions.
    """

    DEFAULT_BID_TURNS = 5
    DEFAULT_MARKET_TURNS = 3
    DEFAULT_BID_PRICE = 25.0

    def __init__(
        self,
        db_path: str | Path = "data/sniffer_data.db",
        fallback_db_path: str | Path = "data/market_data.db",
    ):
        db_path = Path(db_path)
        if not db_path.exists():
            db_path = Path(fallback_db_path)
        
        self._analyzer = DataAnalyzer(db_path)
        self._current_turn: int | None = None

    @property
    def current_turn(self) -> int:
        if self._current_turn is None:
            self._current_turn = self._analyzer.get_current_turn()
        return self._current_turn

    def set_current_turn(self, turn_id: int) -> None:
        """Override current turn (useful when game state is known)."""
        self._current_turn = turn_id

    def get_bidding_context(
        self,
        ingredients: list[str] | None = None,
        last_n_turns: int | None = None,
    ) -> BiddingContext:
        """Get context for auction bidding decisions.
        
        Args:
            ingredients: List of ingredients to get prices for. If None, returns all.
            last_n_turns: Time window for historical data. Defaults to DEFAULT_BID_TURNS.
        
        Returns:
            BiddingContext with suggested prices, hot ingredients, and competitor info.
        """
        if last_n_turns is None:
            last_n_turns = self.DEFAULT_BID_TURNS

        context = BiddingContext()

        # Get suggested prices for requested ingredients
        if ingredients:
            for ing in ingredients:
                price = self._analyzer.get_recommended_bid_price(
                    ing, percentile=0.75, last_n_turns=last_n_turns
                )
                context.suggested_prices[ing] = price if price else self.DEFAULT_BID_PRICE
                
                # Get price range
                stats = self._analyzer.get_winning_bid_stats(ing, last_n_turns=last_n_turns)
                if stats:
                    s = stats[0]
                    context.price_ranges[ing] = {
                        "min": s.min_winning_price or self.DEFAULT_BID_PRICE,
                        "avg": s.avg_winning_price or self.DEFAULT_BID_PRICE,
                        "max": s.max_winning_price or self.DEFAULT_BID_PRICE,
                    }

        # Get hot ingredients (high competition)
        hot = self._analyzer.get_hot_ingredients(last_n_turns=last_n_turns, limit=10)
        context.hot_ingredients = [h["ingredient"] for h in hot if h.get("num_bidders", 0) >= 2]

        # Get competitor budgets
        competitors = self._analyzer.get_competitor_budgets(self.current_turn)
        context.competitor_budgets = {
            c["restaurant_name"]: c["balance"]
            for c in competitors
            if c.get("restaurant_name") and c.get("balance") is not None
        }

        return context

    def get_trading_context(
        self,
        inventory: dict[str, int] | None = None,
        last_n_turns: int | None = None,
    ) -> TradingContext:
        """Get context for market trading decisions.
        
        Args:
            inventory: Current inventory to identify selling opportunities.
            last_n_turns: Time window for historical data. Defaults to DEFAULT_MARKET_TURNS.
        
        Returns:
            TradingContext with spreads, arbitrage opportunities, and demand info.
        """
        if last_n_turns is None:
            last_n_turns = self.DEFAULT_MARKET_TURNS

        context = TradingContext()

        # Get current market spreads
        spreads = self._analyzer.get_current_market_spread(self.current_turn)
        context.spreads = spreads

        # Identify arbitrage opportunities
        context.arbitrage_opportunities = [
            s for s in spreads if s.get("arbitrage_opportunity")
        ]

        # Get high demand ingredients (many BUY orders)
        high_demand = [
            s["ingredient"] for s in spreads
            if s.get("buy_volume", 0) > s.get("sell_volume", 0)
        ]
        
        # Cross-reference with inventory if provided
        if inventory:
            context.high_demand_ingredients = [
                ing for ing in high_demand if inventory.get(ing, 0) > 0
            ]
        else:
            context.high_demand_ingredients = high_demand

        return context

    def get_pricing_context(
        self,
        recipe_ingredients: dict[str, dict[str, int]] | None = None,
        last_n_turns: int | None = None,
    ) -> PricingContext:
        """Get context for menu pricing decisions.
        
        Args:
            recipe_ingredients: Dict of recipe_name -> {ingredient: quantity}.
            last_n_turns: Time window for historical data. Defaults to DEFAULT_BID_TURNS.
        
        Returns:
            PricingContext with ingredient costs and competitor prices.
        """
        if last_n_turns is None:
            last_n_turns = self.DEFAULT_BID_TURNS

        context = PricingContext()

        # Get ingredient costs from recent auctions
        all_stats = self._analyzer.get_winning_bid_stats(last_n_turns=last_n_turns)
        for stat in all_stats:
            if stat.avg_winning_price:
                context.ingredient_costs[stat.ingredient] = stat.avg_winning_price

        # Get competitor dish prices from recent turns
        conn = self._analyzer._get_conn()
        query = """
            SELECT dish_name, price
            FROM competitor_menus
            WHERE turn_id >= (SELECT COALESCE(MAX(turn_id), 0) - ? FROM turns)
              AND price > 0
        """
        rows = conn.execute(query, (last_n_turns,)).fetchall()
        for row in rows:
            dish = row["dish_name"]
            price = row["price"]
            if dish not in context.competitor_dish_prices:
                context.competitor_dish_prices[dish] = []
            context.competitor_dish_prices[dish].append(price)

        return context

    def get_full_context(
        self,
        ingredients: list[str] | None = None,
        inventory: dict[str, int] | None = None,
        recipe_ingredients: dict[str, dict[str, int]] | None = None,
    ) -> dict[str, Any]:
        """Get all context types in a single call.
        
        Returns a dict with keys: bidding, trading, pricing.
        """
        return {
            "bidding": self.get_bidding_context(ingredients).to_dict(),
            "trading": self.get_trading_context(inventory).to_dict(),
            "pricing": self.get_pricing_context(recipe_ingredients).to_dict(),
        }

    def get_suggested_bid(
        self,
        ingredient: str,
        competition_level: str = "normal",
        last_n_turns: int | None = None,
    ) -> float:
        """Get a single suggested bid price for an ingredient.
        
        Args:
            ingredient: The ingredient name.
            competition_level: "low", "normal", or "high" - adjusts percentile.
            last_n_turns: Time window for historical data.
        
        Returns:
            Suggested bid price.
        """
        if last_n_turns is None:
            last_n_turns = self.DEFAULT_BID_TURNS

        percentile_map = {"low": 0.5, "normal": 0.75, "high": 0.9}
        percentile = percentile_map.get(competition_level, 0.75)

        price = self._analyzer.get_recommended_bid_price(
            ingredient, percentile=percentile, last_n_turns=last_n_turns
        )
        
        if price is None:
            # Fallback: check if it's a hot ingredient
            hot = self._analyzer.get_hot_ingredients(last_n_turns=last_n_turns)
            hot_names = {h["ingredient"] for h in hot}
            if ingredient in hot_names:
                return self.DEFAULT_BID_PRICE * 1.3
            return self.DEFAULT_BID_PRICE
        
        return price

    def estimate_recipe_cost(
        self,
        ingredients: dict[str, int],
        last_n_turns: int | None = None,
    ) -> float:
        """Estimate the cost of a recipe based on recent auction prices.
        
        Args:
            ingredients: Dict of ingredient_name -> quantity.
            last_n_turns: Time window for historical data.
        
        Returns:
            Estimated total cost.
        """
        if last_n_turns is None:
            last_n_turns = self.DEFAULT_BID_TURNS

        total = 0.0
        for ing, qty in ingredients.items():
            price = self._analyzer.get_recommended_bid_price(
                ing, percentile=0.5, last_n_turns=last_n_turns
            )
            unit_price = price if price else self.DEFAULT_BID_PRICE
            total += unit_price * qty
        
        return total

    def close(self) -> None:
        """Close the underlying database connection."""
        self._analyzer.close()
