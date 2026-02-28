#!/usr/bin/env python3
"""Interactive viewer for collected market data and intelligence."""
import argparse
import sys
from pathlib import Path

from src.data import DataAnalyzer, MarketIntelligence


def print_header(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_section(title: str) -> None:
    print(f"\n--- {title} ---\n")


def cmd_overview(analyzer: DataAnalyzer, intel: MarketIntelligence) -> None:
    """Show database overview and stats."""
    print_header("DATABASE OVERVIEW")
    
    conn = analyzer._get_conn()
    tables = [
        ("turns", "Turni giocati"),
        ("bids", "Bid sottomessi (nostri)"),
        ("bid_history", "Storico bid (tutti)"),
        ("market_entries", "Offerte mercato"),
        ("transactions", "Transazioni"),
        ("recipes", "Ricette"),
        ("restaurant_snapshots", "Snapshot ristoranti"),
        ("competitor_menus", "Menu competitor"),
        ("inventory_snapshots", "Snapshot inventario"),
        ("menu_items", "Menu nostro"),
        ("orders", "Ordini clienti"),
        ("meals", "Pasti serviti"),
    ]
    
    print(f"{'Tabella':<25} {'Descrizione':<30} {'Righe':>10}")
    print("-" * 70)
    
    total = 0
    for table, desc in tables:
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            total += count
            print(f"{table:<25} {desc:<30} {count:>10}")
        except Exception:
            print(f"{table:<25} {desc:<30} {'N/A':>10}")
    
    print("-" * 70)
    print(f"{'TOTALE':<25} {'':<30} {total:>10}")
    
    print(f"\nCurrent turn: {intel.current_turn}")


def cmd_market(analyzer: DataAnalyzer, intel: MarketIntelligence, turn_id: int | None = None) -> None:
    """Show current market state."""
    print_header("MARKET STATE")
    
    if turn_id is None:
        turn_id = intel.current_turn
    
    spreads = analyzer.get_current_market_spread(turn_id)
    
    if not spreads:
        print("Nessun dato di mercato disponibile.")
        return
    
    print(f"Turn: {turn_id}\n")
    print(f"{'Ingrediente':<35} {'SELL':>10} {'BUY':>10} {'Spread':>10} {'Arbitr.':>8}")
    print("-" * 80)
    
    for s in spreads:
        sell = f"{s['best_sell_price']:.0f}" if s.get('best_sell_price') else "-"
        buy = f"{s['best_buy_price']:.0f}" if s.get('best_buy_price') else "-"
        spread = f"{s['spread']:.0f}" if s.get('spread') is not None else "-"
        arb = "YES" if s.get('arbitrage_opportunity') else ""
        print(f"{s['ingredient']:<35} {sell:>10} {buy:>10} {spread:>10} {arb:>8}")


def cmd_arbitrage(analyzer: DataAnalyzer, intel: MarketIntelligence) -> None:
    """Show arbitrage opportunities."""
    print_header("ARBITRAGE OPPORTUNITIES")
    
    trading_ctx = intel.get_trading_context()
    
    if not trading_ctx.arbitrage_opportunities:
        print("Nessuna opportunità di arbitraggio trovata.")
        return
    
    print(f"{'Ingrediente':<35} {'Compra a':>12} {'Vendi a':>12} {'Profitto':>12}")
    print("-" * 75)
    
    sorted_opps = sorted(
        trading_ctx.arbitrage_opportunities,
        key=lambda x: (x.get('best_buy_price', 0) or 0) - (x.get('best_sell_price', 0) or 0),
        reverse=True
    )
    
    for opp in sorted_opps[:20]:
        sell = opp.get('best_sell_price', 0) or 0
        buy = opp.get('best_buy_price', 0) or 0
        profit = buy - sell
        print(f"{opp['ingredient']:<35} {sell:>12.0f} {buy:>12.0f} {profit:>12.0f}")


def cmd_competitors(analyzer: DataAnalyzer, intel: MarketIntelligence, turn_id: int | None = None) -> None:
    """Show competitor status."""
    print_header("COMPETITOR STATUS")
    
    if turn_id is None:
        turn_id = intel.current_turn
    
    competitors = analyzer.get_competitor_budgets(turn_id)
    
    if not competitors:
        print("Nessun dato sui competitor disponibile.")
        return
    
    print(f"Turn: {turn_id}\n")
    print(f"{'ID':>4} {'Nome':<30} {'Balance':>12} {'Reputation':>12} {'Open':>6}")
    print("-" * 70)
    
    for c in competitors:
        is_open = "Yes" if c.get('is_open') else "No"
        balance = f"{c['balance']:.0f}" if c.get('balance') is not None else "-"
        rep = f"{c['reputation']:.0f}" if c.get('reputation') is not None else "-"
        print(f"{c.get('restaurant_id', '-'):>4} {c.get('restaurant_name', ''):<30} {balance:>12} {rep:>12} {is_open:>6}")


def cmd_hot(analyzer: DataAnalyzer, last_n_turns: int = 3) -> None:
    """Show hot ingredients (most contested)."""
    print_header(f"HOT INGREDIENTS (ultimi {last_n_turns} turni)")
    
    hot = analyzer.get_hot_ingredients(last_n_turns=last_n_turns, limit=20)
    
    if not hot:
        print("Nessun dato sugli ingredienti contesi.")
        return
    
    print(f"{'Ingrediente':<35} {'Bid':>8} {'Bidders':>10} {'Avg Price':>12} {'Max Price':>12}")
    print("-" * 80)
    
    for h in hot:
        avg = f"{h['avg_bid_price']:.1f}" if h.get('avg_bid_price') else "-"
        max_p = f"{h['max_bid_price']:.1f}" if h.get('max_bid_price') else "-"
        print(f"{h['ingredient']:<35} {h.get('bid_count', 0):>8} {h.get('num_bidders', 0):>10} {avg:>12} {max_p:>12}")


def cmd_recipes(analyzer: DataAnalyzer, limit: int = 20) -> None:
    """Show collected recipes."""
    print_header(f"RECIPES (top {limit} by prestige)")
    
    recipes = analyzer.get_recipes_list()
    
    if not recipes:
        print("Nessuna ricetta trovata.")
        return
    
    print(f"{'Ricetta':<45} {'Prestige':>10} {'Ingredienti':>12}")
    print("-" * 70)
    
    for r in recipes[:limit]:
        ing_count = len(r.get('ingredients', {}))
        prestige = r.get('prestige', 0) or 0
        print(f"{r['name']:<45} {prestige:>10} {ing_count:>12}")


def cmd_recipe_detail(analyzer: DataAnalyzer, intel: MarketIntelligence, recipe_name: str) -> None:
    """Show recipe details with cost estimation."""
    print_header(f"RECIPE: {recipe_name}")
    
    recipes = analyzer.get_recipes_list()
    recipe = next((r for r in recipes if r['name'].lower() == recipe_name.lower()), None)
    
    if not recipe:
        print(f"Ricetta '{recipe_name}' non trovata.")
        print("\nRicette disponibili (prime 10):")
        for r in recipes[:10]:
            print(f"  - {r['name']}")
        return
    
    print(f"Nome: {recipe['name']}")
    print(f"Prestige: {recipe.get('prestige', 'N/A')}")
    print(f"Tempo preparazione: {recipe.get('preparation_time_ms', 'N/A')} ms")
    
    ingredients = recipe.get('ingredients', {})
    if ingredients:
        print_section("Ingredienti")
        print(f"{'Ingrediente':<35} {'Quantità':>10} {'Costo stimato':>15}")
        print("-" * 65)
        
        total_cost = 0
        for ing, qty in ingredients.items():
            price = intel.get_suggested_bid(ing)
            cost = price * qty
            total_cost += cost
            print(f"{ing:<35} {qty:>10} {cost:>15.1f}")
        
        print("-" * 65)
        print(f"{'TOTALE':<35} {'':<10} {total_cost:>15.1f}")
        print(f"\nPrezzo vendita suggerito (markup 50%): {total_cost * 1.5:.0f}")


def cmd_bidding(intel: MarketIntelligence, ingredients: list[str] | None = None) -> None:
    """Show bidding intelligence."""
    print_header("BIDDING INTELLIGENCE")
    
    if not ingredients:
        # Get some common ingredients from recipes
        recipes = intel._analyzer.get_recipes_list()
        all_ings = set()
        for r in recipes[:20]:
            all_ings.update(r.get('ingredients', {}).keys())
        ingredients = list(all_ings)[:15]
    
    ctx = intel.get_bidding_context(ingredients)
    
    print(ctx.to_prompt_string())
    
    if ctx.price_ranges:
        print_section("Price Ranges")
        print(f"{'Ingrediente':<35} {'Min':>10} {'Avg':>10} {'Max':>10}")
        print("-" * 70)
        for ing, pr in sorted(ctx.price_ranges.items()):
            print(f"{ing:<35} {pr.get('min', 0):>10.1f} {pr.get('avg', 0):>10.1f} {pr.get('max', 0):>10.1f}")


def cmd_pricing(intel: MarketIntelligence) -> None:
    """Show pricing intelligence."""
    print_header("PRICING INTELLIGENCE")
    
    ctx = intel.get_pricing_context()
    
    if ctx.ingredient_costs:
        print_section("Costi Ingredienti (da aste recenti)")
        print(f"{'Ingrediente':<40} {'Costo/unità':>15}")
        print("-" * 60)
        for ing, cost in sorted(ctx.ingredient_costs.items()):
            print(f"{ing:<40} {cost:>15.1f}")
    else:
        print("Nessun dato sui costi ingredienti (servono aste giocate).")
    
    if ctx.competitor_dish_prices:
        print_section("Prezzi Piatti Competitor")
        print(f"{'Piatto':<45} {'Min':>8} {'Avg':>8} {'Max':>8} {'#':>5}")
        print("-" * 80)
        for dish, prices in sorted(ctx.competitor_dish_prices.items()):
            if prices:
                avg = sum(prices) / len(prices)
                print(f"{dish[:44]:<45} {min(prices):>8.0f} {avg:>8.0f} {max(prices):>8.0f} {len(prices):>5}")


def cmd_trading(intel: MarketIntelligence, inventory: dict[str, int] | None = None) -> None:
    """Show trading intelligence."""
    print_header("TRADING INTELLIGENCE")
    
    ctx = intel.get_trading_context(inventory)
    print(ctx.to_prompt_string())


def main():
    parser = argparse.ArgumentParser(
        description="View collected market data and intelligence",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  overview     Database statistics
  market       Current market state (BUY/SELL offers)
  arbitrage    Arbitrage opportunities
  competitors  Competitor status (balance, reputation)
  hot          Hot ingredients (most contested)
  recipes      List recipes
  recipe NAME  Recipe details with cost estimation
  bidding      Bidding intelligence
  pricing      Pricing intelligence  
  trading      Trading intelligence

Examples:
  python view_data.py overview
  python view_data.py market
  python view_data.py recipe "Nebulosa Galattica"
  python view_data.py hot --turns 5
        """
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="overview",
        help="Command to run (default: overview)"
    )
    parser.add_argument(
        "args",
        nargs="*",
        help="Additional arguments for the command"
    )
    parser.add_argument(
        "--db",
        default="data/market_data.db",
        help="Path to database (default: data/market_data.db)"
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=3,
        help="Number of turns to look back (default: 3)"
    )
    parser.add_argument(
        "--turn",
        type=int,
        default=None,
        help="Specific turn ID to query"
    )

    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        db_path = Path("data/market_data.db")
    
    if not db_path.exists():
        print(f"Database non trovato: {args.db}")
        print("Esegui prima lo sniffer o una partita per raccogliere dati.")
        sys.exit(1)

    analyzer = DataAnalyzer(db_path)
    intel = MarketIntelligence(db_path)

    try:
        cmd = args.command.lower()
        
        if cmd == "overview":
            cmd_overview(analyzer, intel)
        elif cmd == "market":
            cmd_market(analyzer, intel, args.turn)
        elif cmd == "arbitrage":
            cmd_arbitrage(analyzer, intel)
        elif cmd == "competitors":
            cmd_competitors(analyzer, intel, args.turn)
        elif cmd == "hot":
            cmd_hot(analyzer, args.turns)
        elif cmd == "recipes":
            cmd_recipes(analyzer)
        elif cmd == "recipe":
            if not args.args:
                print("Specifica il nome della ricetta: python view_data.py recipe 'Nome Ricetta'")
                sys.exit(1)
            recipe_name = " ".join(args.args)
            cmd_recipe_detail(analyzer, intel, recipe_name)
        elif cmd == "bidding":
            ingredients = args.args if args.args else None
            cmd_bidding(intel, ingredients)
        elif cmd == "pricing":
            cmd_pricing(intel)
        elif cmd == "trading":
            cmd_trading(intel)
        else:
            print(f"Comando sconosciuto: {cmd}")
            parser.print_help()
            sys.exit(1)

    finally:
        analyzer.close()
        intel.close()


if __name__ == "__main__":
    main()
