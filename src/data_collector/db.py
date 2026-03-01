"""Database schema and connection utilities for Market Intelligence data collection."""
import sqlite3
from pathlib import Path

SCHEMA = """
-- Storico bid aste
CREATE TABLE IF NOT EXISTS bid_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    turn_id INTEGER NOT NULL,
    restaurant_id INTEGER NOT NULL,
    ingredient TEXT NOT NULL,
    bid_amount REAL NOT NULL,
    quantity INTEGER NOT NULL,
    won BOOLEAN,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Storico pasti serviti
CREATE TABLE IF NOT EXISTS meals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    turn_id INTEGER NOT NULL,
    restaurant_id INTEGER NOT NULL,
    customer_id TEXT,
    client_name TEXT,
    dish_name TEXT,
    price REAL,
    executed BOOLEAN,
    order_text TEXT,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Storico market entries
CREATE TABLE IF NOT EXISTS market_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL,
    turn_id INTEGER NOT NULL,
    restaurant_id INTEGER NOT NULL,
    side TEXT NOT NULL,
    ingredient_name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    price REAL NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Snapshot ristoranti
CREATE TABLE IF NOT EXISTS restaurant_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    turn_id INTEGER NOT NULL,
    restaurant_id INTEGER NOT NULL,
    name TEXT,
    balance REAL,
    reputation REAL,
    is_open BOOLEAN,
    menu_json TEXT,
    inventory_json TEXT,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Blog posts visti (per rilevare "nuova notizia")
CREATE TABLE IF NOT EXISTS blog_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    first_seen_turn_id INTEGER NOT NULL,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Eventi SSE ricevuti
CREATE TABLE IF NOT EXISTS sse_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    turn_id INTEGER,
    event_type TEXT NOT NULL,
    event_data TEXT,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indici per query frequenti
CREATE INDEX IF NOT EXISTS idx_bid_history_turn ON bid_history(turn_id);
CREATE INDEX IF NOT EXISTS idx_bid_history_ingredient ON bid_history(ingredient);
CREATE INDEX IF NOT EXISTS idx_meals_turn ON meals(turn_id);
CREATE INDEX IF NOT EXISTS idx_meals_dish ON meals(dish_name);
CREATE INDEX IF NOT EXISTS idx_market_entries_turn ON market_entries(turn_id);
CREATE INDEX IF NOT EXISTS idx_market_entries_ingredient ON market_entries(ingredient_name);
CREATE INDEX IF NOT EXISTS idx_restaurant_snapshots_turn ON restaurant_snapshots(turn_id);
CREATE INDEX IF NOT EXISTS idx_sse_events_turn ON sse_events(turn_id);
CREATE INDEX IF NOT EXISTS idx_sse_events_type ON sse_events(event_type);
"""


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    """Get a SQLite connection with row factory enabled."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str | Path) -> None:
    """Initialize the database schema. Creates tables if they don't exist."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
