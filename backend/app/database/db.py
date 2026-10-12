from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from backend.app.paths import DB_PATH, ensure_dirs

SCHEMA = """
CREATE TABLE IF NOT EXISTS sim_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    status TEXT NOT NULL DEFAULT 'idle',
    clock REAL NOT NULL DEFAULT 0,
    event_index INTEGER NOT NULL DEFAULT 0,
    speed REAL NOT NULL DEFAULT 8,
    start_day INTEGER NOT NULL DEFAULT 7,
    total_events INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS app_orders (
    order_id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    cell INTEGER NOT NULL,
    t REAL NOT NULL,
    day INTEGER NOT NULL,
    hour INTEGER NOT NULL,
    dow INTEGER NOT NULL,
    value INTEGER NOT NULL,
    n_items INTEGER NOT NULL,
    small INTEGER NOT NULL,
    status TEXT NOT NULL,
    wait_minutes INTEGER,
    radius_m INTEGER,
    partner_order_id INTEGER,
    placed_wallclock TEXT,
    customer_name TEXT
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    item_id TEXT NOT NULL,
    item_type TEXT,
    unit_price INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    FOREIGN KEY(order_id) REFERENCES app_orders(order_id)
);

CREATE TABLE IF NOT EXISTS status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    sim_t REAL NOT NULL,
    note TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    wait_minutes INTEGER NOT NULL,
    radius_m INTEGER NOT NULL,
    probability REAL NOT NULL,
    predicted_class INTEGER NOT NULL,
    sim_t REAL NOT NULL,
    feature_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    wait_minutes INTEGER,
    radius_m INTEGER,
    probability REAL,
    partner_order_id INTEGER,
    saving REAL,
    delay REAL,
    elapsed_wait REAL,
    reason TEXT,
    sim_t REAL NOT NULL,
    unique_key TEXT UNIQUE
);

INSERT OR IGNORE INTO sim_state (id) VALUES (1);
"""


def connect(path: Path | None = None) -> sqlite3.Connection:
    ensure_dirs()
    db_path = path or DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection | None = None) -> None:
    own = conn is None
    conn = conn or connect()
    conn.executescript(SCHEMA)
    conn.commit()
    if own:
        conn.close()


@contextmanager
def get_conn():
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
