"""
db.py — SQLite/PostgreSQL storage for the expense tracker.

Single table "txns":
    id          INTEGER/SERIAL PRIMARY KEY
    date        TEXT      (YYYY-MM-DD, the date the txn happened)
    category    TEXT
    amount      REAL
    note        TEXT
    type        TEXT      ("expense" | "income")
    chat_id     INTEGER   (Telegram chat that logged it)
    created_at  TEXT      (ISO timestamp, when the row was inserted)
"""

import os
import sqlite3
from datetime import datetime, date
from pathlib import Path
from dotenv import load_dotenv

# Load env variables from .env if present
load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
DB_PATH = Path(__file__).parent / "expenses.db"

IS_POSTGRES = bool(DATABASE_URL)

if IS_POSTGRES:
    import psycopg2
    from psycopg2.extras import DictCursor

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS txns (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT NOT NULL,
    category    TEXT NOT NULL,
    amount      REAL NOT NULL,
    note        TEXT,
    type        TEXT NOT NULL CHECK(type IN ('expense', 'income')),
    chat_id     BIGINT,
    created_at  TEXT NOT NULL
);
"""

POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS txns (
    id          SERIAL PRIMARY KEY,
    date        VARCHAR(10) NOT NULL,
    category    VARCHAR(50) NOT NULL,
    amount      DOUBLE PRECISION NOT NULL,
    note        TEXT,
    type        VARCHAR(10) NOT NULL CHECK(type IN ('expense', 'income')),
    chat_id     BIGINT,
    created_at  VARCHAR(30) NOT NULL
);
"""


def _connect():
    if IS_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur:
            cur.execute(POSTGRES_SCHEMA)
        conn.commit()
        return conn
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute(SQLITE_SCHEMA)
        conn.commit()
        return conn


def _run_query(conn, query, params=()):
    if IS_POSTGRES:
        query = query.replace("?", "%s")
        cur = conn.cursor(cursor_factory=DictCursor)
        cur.execute(query, params)
        return cur
    else:
        return conn.execute(query, params)


def init_db():
    """Ensure the database file and schema exist. Safe to call repeatedly."""
    conn = _connect()
    conn.close()


def add(amount, category, note, txn_type, chat_id=None, txn_date=None):
    """Insert a new transaction. Returns the new row's id."""
    conn = _connect()
    txn_date = txn_date or date.today().isoformat()
    created_at = datetime.now().isoformat(timespec="seconds")
    
    query = """INSERT INTO txns (date, category, amount, note, type, chat_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)"""
               
    if IS_POSTGRES:
        query = query.replace("?", "%s") + " RETURNING id"
        cur = conn.cursor()
        cur.execute(query, (txn_date, category, amount, note, txn_type, chat_id, created_at))
        new_id = cur.fetchone()[0]
    else:
        cur = conn.execute(query, (txn_date, category, amount, note, txn_type, chat_id, created_at))
        new_id = cur.lastrowid
        
    conn.commit()
    conn.close()
    return new_id


def undo_last(chat_id=None):
    """
    Delete the most recently inserted transaction (optionally scoped to a
    chat_id). Returns the deleted row as a dict, or None if nothing to undo.
    """
    conn = _connect()
    if chat_id is not None:
        query = "SELECT * FROM txns WHERE chat_id = ? ORDER BY id DESC LIMIT 1"
        cur = _run_query(conn, query, (chat_id,))
    else:
        query = "SELECT * FROM txns ORDER BY id DESC LIMIT 1"
        cur = _run_query(conn, query)

    row = cur.fetchone()
    if row is None:
        conn.close()
        return None

    delete_query = "DELETE FROM txns WHERE id = ?"
    _run_query(conn, delete_query, (row["id"],))
    conn.commit()
    conn.close()
    return dict(row)


def all_rows():
    """Return every transaction as a list of dicts, oldest first."""
    conn = _connect()
    query = "SELECT * FROM txns ORDER BY date ASC, id ASC"
    cur = _run_query(conn, query)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def month_total(month):
    """
    Sum of expenses for a given month, e.g. month_total("2026-06").
    Income is excluded from the total (it's a separate concern on the
    dashboard / total command).
    """
    conn = _connect()
    query = """SELECT COALESCE(SUM(amount), 0) AS total
               FROM txns
               WHERE type = 'expense' AND date LIKE ?"""
    cur = _run_query(conn, query, (f"{month}%",))
    row = cur.fetchone()
    conn.close()
    return row["total"]


def month_income(month):
    conn = _connect()
    query = """SELECT COALESCE(SUM(amount), 0) AS total
               FROM txns
               WHERE type = 'income' AND date LIKE ?"""
    cur = _run_query(conn, query, (f"{month}%",))
    row = cur.fetchone()
    conn.close()
    return row["total"]


def category_totals(month):
    """Dict of {category: total_spent} for expenses in a given month."""
    conn = _connect()
    query = """SELECT category, COALESCE(SUM(amount), 0) AS total
               FROM txns
               WHERE type = 'expense' AND date LIKE ?
               GROUP BY category
               ORDER BY total DESC"""
    cur = _run_query(conn, query, (f"{month}%",))
    rows = cur.fetchall()
    conn.close()
    return {r["category"]: r["total"] for r in rows}


if __name__ == "__main__":
    # quick smoke test
    import os

    if not IS_POSTGRES:
        if DB_PATH.exists():
            os.remove(DB_PATH)
    else:
        conn = _connect()
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS txns")
        conn.commit()
        conn.close()

    init_db()
    add(500, "travel", "ola", "expense", chat_id=1, txn_date="2026-06-01")
    add(420, "food", "swiggy dinner", "expense", chat_id=1, txn_date="2026-06-02")
    add(75000, "income", "salary", "income", chat_id=1, txn_date="2026-06-01")
    print("all_rows:", all_rows())
    print("month_total 2026-06:", month_total("2026-06"))
    print("month_income 2026-06:", month_income("2026-06"))
    print("category_totals 2026-06:", category_totals("2026-06"))
    deleted = undo_last(chat_id=1)
    print("undo_last:", deleted)
    print("all_rows after undo:", all_rows())

