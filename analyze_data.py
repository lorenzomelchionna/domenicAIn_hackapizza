#!/usr/bin/env python3
"""CLI tool to analyze collected market data."""
import argparse
import sys
from pathlib import Path

from src.data import DataAnalyzer


def main():
    parser = argparse.ArgumentParser(description="Analyze Hackapizza market data")
    parser.add_argument(
        "--db",
        default="data/market_data.db",
        help="Path to SQLite database (default: data/market_data.db)",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Bid stats command
    bid_parser = subparsers.add_parser("bids", help="Show bid statistics")
    bid_parser.add_argument("--ingredient", "-i", help="Filter by ingredient")

    # Turn summary command
    turn_parser = subparsers.add_parser("turns", help="Show turn summaries")
    turn_parser.add_argument("--turn", "-t", type=int, help="Specific turn ID")

    # Profitability command
    subparsers.add_parser("profit", help="Show dish profitability analysis")

    # Market opportunities command
    subparsers.add_parser("market", help="Show market trading opportunities")

    # Ingredient demand command
    subparsers.add_parser("demand", help="Show ingredient demand analysis")

    # Recipes command
    subparsers.add_parser("recipes", help="Show collected recipes")

    # Restaurants command
    subparsers.add_parser("restaurants", help="Show restaurant snapshots")

    # Stats command
    subparsers.add_parser("stats", help="Show database statistics")

    # Export command
    export_parser = subparsers.add_parser("export", help="Export data to CSV")
    export_parser.add_argument(
        "--output",
        "-o",
        default="data/exports",
        help="Output directory (default: data/exports)",
    )

    args = parser.parse_args()

    if not Path(args.db).exists():
        print(f"Database not found: {args.db}")
        print("Run a game first to collect data.")
        sys.exit(1)

    analyzer = DataAnalyzer(args.db)

    try:
        if args.command == "bids":
            stats = analyzer.get_winning_bid_stats(args.ingredient)
            if not stats:
                print("No bid data found.")
                return
            print(f"\n{'Ingredient':<20} {'Bids':>6} {'Wins':>6} {'Win%':>7} {'Avg Bid':>10} {'Avg Win':>10}")
            print("-" * 70)
            for s in stats:
                avg_win = f"{s.avg_winning_price:.2f}" if s.avg_winning_price else "N/A"
                print(
                    f"{s.ingredient:<20} {s.total_bids:>6} {s.wins:>6} {s.win_rate*100:>6.1f}% "
                    f"{s.avg_bid_price:>10.2f} {avg_win:>10}"
                )

            # Show recommended prices
            print("\n\nRecommended bid prices (75th percentile of winning bids):")
            print("-" * 40)
            for s in stats:
                if s.wins > 0:
                    rec = analyzer.get_recommended_bid_price(s.ingredient)
                    if rec:
                        print(f"  {s.ingredient}: {rec:.2f}")

        elif args.command == "turns":
            if args.turn:
                summary = analyzer.get_turn_summary(args.turn)
                if not summary:
                    print(f"Turn {args.turn} not found.")
                    return
                summaries = [summary]
            else:
                summaries = analyzer.get_all_turns_summary()

            if not summaries:
                print("No turn data found.")
                return

            print(f"\n{'Turn':>5} {'Balance Δ':>12} {'Rep Δ':>8} {'Bids':>6} {'Won':>5} {'Orders':>7} {'Revenue':>10}")
            print("-" * 70)
            for s in summaries:
                print(
                    f"{s['turn_id']:>5} {s['balance_change']:>+12.2f} {s['reputation_change']:>+8.2f} "
                    f"{s['bids_total']:>6} {s['bids_won']:>5} {s['orders_total']:>7} {s['revenue']:>10.2f}"
                )

        elif args.command == "profit":
            dishes = analyzer.get_price_vs_cost_analysis()
            if not dishes:
                print("No dish data found.")
                return
            print(f"\n{'Dish':<30} {'Served':>7} {'Revenue':>10} {'Avg Price':>10} {'Margin':>8}")
            print("-" * 75)
            for d in dishes:
                margin = f"{d.avg_margin*100:.1f}%" if d.avg_margin else "N/A"
                print(
                    f"{d.dish_name:<30} {d.times_served:>7} {d.total_revenue:>10.2f} "
                    f"{d.avg_price:>10.2f} {margin:>8}"
                )

        elif args.command == "market":
            opportunities = analyzer.get_market_opportunities()
            if not opportunities:
                print("No market data found.")
                return
            print(f"\n{'Ingredient':<20} {'Avg Buy':>10} {'Avg Sell':>10} {'Spread':>10} {'Buy Vol':>8} {'Sell Vol':>9}")
            print("-" * 75)
            for o in opportunities:
                print(
                    f"{o.ingredient:<20} {o.avg_buy_price:>10.2f} {o.avg_sell_price:>10.2f} "
                    f"{o.spread:>+10.2f} {o.buy_volume:>8} {o.sell_volume:>9}"
                )

        elif args.command == "demand":
            demand = analyzer.get_ingredient_demand()
            if not demand:
                print("No demand data found.")
                return
            print(f"\n{'Ingredient':<20} {'Bid Count':>10} {'Total Qty':>10} {'Avg Price':>10}")
            print("-" * 55)
            for d in demand:
                print(
                    f"{d['ingredient']:<20} {d['bid_count']:>10} {d['total_quantity_bid']:>10} "
                    f"{d['avg_bid_price']:>10.2f}"
                )

        elif args.command == "recipes":
            conn = analyzer._get_conn()
            rows = conn.execute(
                "SELECT name, prestige, preparation_time_ms, ingredients_json FROM recipes ORDER BY prestige DESC LIMIT 20"
            ).fetchall()
            if not rows:
                print("No recipes found.")
                return
            print(f"\n{'Recipe':<40} {'Prestige':>8} {'Time(ms)':>10}")
            print("-" * 65)
            for row in rows:
                print(f"{row[0]:<40} {row[1] or 0:>8} {row[2] or 0:>10}")

        elif args.command == "restaurants":
            conn = analyzer._get_conn()
            rows = conn.execute(
                """SELECT restaurant_id, restaurant_name, balance, reputation, is_open, timestamp 
                   FROM restaurant_snapshots 
                   ORDER BY timestamp DESC LIMIT 30"""
            ).fetchall()
            if not rows:
                print("No restaurant snapshots found.")
                return
            print(f"\n{'ID':>4} {'Name':<25} {'Balance':>10} {'Rep':>6} {'Open':>5}")
            print("-" * 60)
            for row in rows:
                is_open = "Yes" if row[4] else "No"
                print(f"{row[0]:>4} {(row[1] or ''):<25} {row[2] or 0:>10.0f} {row[3] or 0:>6.0f} {is_open:>5}")

        elif args.command == "stats":
            conn = analyzer._get_conn()
            tables = [
                "turns", "bids", "market_entries", "transactions", 
                "inventory_snapshots", "menu_items", "orders", 
                "competitor_menus", "bid_history", "recipes", 
                "restaurant_snapshots", "meals"
            ]
            print("\nDatabase Statistics:")
            print("-" * 40)
            total = 0
            for table in tables:
                try:
                    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    total += count
                    print(f"  {table:<25} {count:>8} rows")
                except Exception:
                    print(f"  {table:<25} {'N/A':>8}")
            print("-" * 40)
            print(f"  {'TOTAL':<25} {total:>8} rows")

        elif args.command == "export":
            results = analyzer.export_all_to_csv(args.output)
            print(f"\nExported to {args.output}:")
            for table, count in results.items():
                status = f"{count} rows" if count >= 0 else "failed"
                print(f"  {table}.csv: {status}")

        else:
            parser.print_help()

    finally:
        analyzer.close()


if __name__ == "__main__":
    main()
