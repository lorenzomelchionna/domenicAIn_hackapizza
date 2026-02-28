#!/usr/bin/env python3
"""CLI tool to inspect the Market Intelligence database."""
import argparse
import json
import sys
from pathlib import Path

from .db import get_connection, init_db
from .queries import (
    get_all_turns,
    get_avg_bid_by_ingredient,
    get_competitor_performance,
    get_dish_popularity,
    get_ingredient_market_prices,
    get_turn_summary,
    get_winning_bid_stats,
)


def get_db_path() -> Path:
    """Get database path from config or default."""
    try:
        from src.config import DB_PATH
        return Path(DB_PATH)
    except ImportError:
        return Path("data/hackapizza.db")


def cmd_stats(args: argparse.Namespace) -> None:
    """Show database population statistics."""
    db_path = args.db or get_db_path()
    if not Path(db_path).exists():
        print(f"Database not found: {db_path}")
        sys.exit(1)

    conn = get_connection(db_path)
    try:
        print(f"\n{'='*50}")
        print(f"  DATABASE: {db_path}")
        print(f"{'='*50}\n")

        tables = [
            ("bid_history", "Bid History"),
            ("meals", "Meals"),
            ("market_entries", "Market Entries"),
            ("restaurant_snapshots", "Restaurant Snapshots"),
            ("sse_events", "SSE Events"),
        ]

        total = 0
        for table, label in tables:
            cursor = conn.execute(f"SELECT COUNT(*) as c FROM {table}")
            count = cursor.fetchone()["c"]
            total += count
            print(f"  {label:25} {count:>8} records")

        print(f"  {'-'*35}")
        print(f"  {'TOTAL':25} {total:>8} records\n")

        turns = get_all_turns(db_path)
        if turns:
            print(f"  Turns collected: {len(turns)}")
            print(f"  Turn range: {min(turns)} - {max(turns)}\n")
        else:
            print("  No turns collected yet.\n")

    finally:
        conn.close()


def cmd_turns(args: argparse.Namespace) -> None:
    """Show summary for each turn."""
    db_path = args.db or get_db_path()
    if not Path(db_path).exists():
        print(f"Database not found: {db_path}")
        sys.exit(1)

    turns = get_all_turns(db_path)
    if not turns:
        print("No turns collected yet.")
        return

    print(f"\n{'Turn':<8} {'Bids':<8} {'Meals':<8} {'Market':<8} {'Snapshots':<10} {'Events':<8}")
    print("-" * 58)

    for turn_id in turns:
        summary = get_turn_summary(db_path, turn_id)
        print(
            f"{turn_id:<8} "
            f"{summary['bid_count']:<8} "
            f"{summary['meal_count']:<8} "
            f"{summary['market_entry_count']:<8} "
            f"{summary['restaurant_snapshot_count']:<10} "
            f"{summary['sse_event_count']:<8}"
        )
    print()


def cmd_bids(args: argparse.Namespace) -> None:
    """Show bid statistics by ingredient."""
    db_path = args.db or get_db_path()
    if not Path(db_path).exists():
        print(f"Database not found: {db_path}")
        sys.exit(1)

    if args.winning:
        stats = get_winning_bid_stats(db_path)
        print(f"\n{'Ingredient':<25} {'Avg Win':<10} {'Min':<8} {'Max':<8} {'Count':<8}")
        print("-" * 60)
        for row in stats:
            print(
                f"{row['ingredient']:<25} "
                f"{row['avg_winning_bid']:<10} "
                f"{row['min_winning_bid']:<8} "
                f"{row['max_winning_bid']:<8} "
                f"{row['winning_bids']:<8}"
            )
    else:
        stats = get_avg_bid_by_ingredient(db_path)
        print(f"\n{'Ingredient':<25} {'Avg Bid':<10} {'Min':<8} {'Max':<8} {'Total':<8} {'Win %':<8}")
        print("-" * 70)
        for row in stats:
            print(
                f"{row['ingredient']:<25} "
                f"{row['avg_bid']:<10} "
                f"{row['min_bid']:<8} "
                f"{row['max_bid']:<8} "
                f"{row['total_bids']:<8} "
                f"{row['win_rate']:<8}"
            )
    print()


def cmd_dishes(args: argparse.Namespace) -> None:
    """Show dish popularity statistics."""
    db_path = args.db or get_db_path()
    if not Path(db_path).exists():
        print(f"Database not found: {db_path}")
        sys.exit(1)

    stats = get_dish_popularity(db_path)
    if not stats:
        print("No dish data collected yet.")
        return

    print(f"\n{'Dish':<30} {'Orders':<8} {'Avg Price':<10} {'Executed':<10} {'Success %':<10}")
    print("-" * 70)
    for row in stats:
        print(
            f"{row['dish_name'][:29]:<30} "
            f"{row['order_count']:<8} "
            f"{row['avg_price'] or '-':<10} "
            f"{row['executed_count']:<10} "
            f"{row['success_rate']:<10}"
        )
    print()


def cmd_market(args: argparse.Namespace) -> None:
    """Show market price statistics."""
    db_path = args.db or get_db_path()
    if not Path(db_path).exists():
        print(f"Database not found: {db_path}")
        sys.exit(1)

    stats = get_ingredient_market_prices(db_path)
    if not stats:
        print("No market data collected yet.")
        return

    print(f"\n{'Ingredient':<25} {'Avg Price':<10} {'Min':<8} {'Max':<8} {'Buys':<8} {'Sells':<8}")
    print("-" * 70)
    for row in stats:
        print(
            f"{row['ingredient_name']:<25} "
            f"{row['avg_price']:<10} "
            f"{row['min_price']:<8} "
            f"{row['max_price']:<8} "
            f"{row['buy_count']:<8} "
            f"{row['sell_count']:<8}"
        )
    print()


def cmd_competitors(args: argparse.Namespace) -> None:
    """Show competitor performance."""
    db_path = args.db or get_db_path()
    if not Path(db_path).exists():
        print(f"Database not found: {db_path}")
        sys.exit(1)

    stats = get_competitor_performance(db_path)
    if not stats:
        print("No competitor data collected yet.")
        return

    print(f"\n{'ID':<5} {'Name':<20} {'Balance':<12} {'Reputation':<12} {'Open':<6} {'Last Turn':<10}")
    print("-" * 70)
    for row in stats:
        print(
            f"{row['restaurant_id']:<5} "
            f"{(row['name'] or '-')[:19]:<20} "
            f"{row['balance'] or '-':<12} "
            f"{row['reputation'] or '-':<12} "
            f"{'Yes' if row['is_open'] else 'No':<6} "
            f"{row['last_turn']:<10}"
        )
    print()


def cmd_menus(args: argparse.Namespace) -> None:
    """Show latest menus from all restaurants."""
    db_path = args.db or get_db_path()
    if not Path(db_path).exists():
        print(f"Database not found: {db_path}")
        sys.exit(1)

    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """
            SELECT rs.restaurant_id, rs.name, rs.menu_json, rs.turn_id, rs.id
            FROM restaurant_snapshots rs
            INNER JOIN (
                SELECT restaurant_id, MAX(id) as max_id
                FROM restaurant_snapshots
                GROUP BY restaurant_id
            ) latest ON rs.id = latest.max_id
            ORDER BY rs.restaurant_id
            """
        )
        rows = cursor.fetchall()
        
        if not rows:
            print("No menu data collected yet.")
            return

        print(f"\n{'='*60}")
        for row in rows:
            print(f"\nRestaurant {row['restaurant_id']}: {row['name'] or 'Unknown'} (turn {row['turn_id']})")
            print("-" * 40)
            if row['menu_json']:
                menu_data = json.loads(row['menu_json'])
                # Handle {"items": [...]} structure
                if isinstance(menu_data, dict) and 'items' in menu_data:
                    menu = menu_data['items']
                elif isinstance(menu_data, list):
                    menu = menu_data
                else:
                    menu = []
                
                if menu:
                    for item in menu:
                        if isinstance(item, dict):
                            name = item.get('name', '?')
                            price = item.get('price', '?')
                            print(f"  {name:<40} ${price}")
                        elif isinstance(item, str):
                            print(f"  {item}")
                        else:
                            print(f"  {item}")
                else:
                    print("  (empty menu)")
            else:
                print("  (no menu data)")
        print()

    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Hackapizza Market Intelligence DB Inspector",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--db", type=str, help="Path to SQLite database (default: from config)")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # stats
    subparsers.add_parser("stats", help="Show database population statistics")

    # turns
    subparsers.add_parser("turns", help="Show summary for each turn")

    # bids
    bids_parser = subparsers.add_parser("bids", help="Show bid statistics by ingredient")
    bids_parser.add_argument("--winning", action="store_true", help="Show only winning bid stats")

    # dishes
    subparsers.add_parser("dishes", help="Show dish popularity statistics")

    # market
    subparsers.add_parser("market", help="Show market price statistics")

    # competitors
    subparsers.add_parser("competitors", help="Show competitor performance")

    # menus
    subparsers.add_parser("menus", help="Show latest menus from all restaurants")

    args = parser.parse_args()

    if args.command is None:
        cmd_stats(args)
    elif args.command == "stats":
        cmd_stats(args)
    elif args.command == "turns":
        cmd_turns(args)
    elif args.command == "bids":
        cmd_bids(args)
    elif args.command == "dishes":
        cmd_dishes(args)
    elif args.command == "market":
        cmd_market(args)
    elif args.command == "competitors":
        cmd_competitors(args)
    elif args.command == "menus":
        cmd_menus(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
