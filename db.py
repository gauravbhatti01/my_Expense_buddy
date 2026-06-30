"""
db.py — SQLite storage for the expense tracker.

Single table "txns":
    id          INTEGER PRIMARY KEY
    date        TEXT      (YYYY-MM-DD, the date the txn happened)
    category    TEXT
    amount      REAL
    note        TEXT
    type        TEXT      ("expense" | "income")
    chat_id     INTEGER   (Telegram chat that logged it)
    created_at  TEXT      (ISO timestamp, when the row was inserted)
"""

import sqlite3
from datetime import datetime, date
from pathlib import Path

DB_PATH = Path(__file__).parent / "expenses.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS txns (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT NOT NULL,
    category    TEXT NOT NULL,
    amount      REAL NOT NULL,
    note        TEXT,
    type        TEXT NOT NULL CHECK(type IN ('expense', 'income')),
    chat_id     INTEGER,
    created_at  TEXT NOT NULL
);
"""


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    return conn


def init_db():
    """Ensure the database file and schema exist. Safe to call repeatedly."""
    conn = _connect()
    conn.commit()
    conn.close()


def add(amount, category, note, txn_type, chat_id=None, txn_date=None):
    """Insert a new transaction. Returns the new row's id."""
    conn = _connect()
    txn_date = txn_date or date.today().isoformat()
    created_at = datetime.now().isoformat(timespec="seconds")
    cur = conn.execute(
        """INSERT INTO txns (date, category, amount, note, type, chat_id, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (txn_date, category, amount, note, txn_type, chat_id, created_at),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def undo_last(chat_id=None):
    """
    Delete the most recently inserted transaction (optionally scoped to a
    chat_id). Returns the deleted row as a dict, or None if nothing to undo.
    """
    conn = _connect()
    if chat_id is not None:
        row = conn.execute(
            "SELECT * FROM txns WHERE chat_id = ? ORDER BY id DESC LIMIT 1",
            (chat_id,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM txns ORDER BY id DESC LIMIT 1"
        ).fetchone()

    if row is None:
        conn.close()
        return None

    conn.execute("DELETE FROM txns WHERE id = ?", (row["id"],))
    conn.commit()
    conn.close()
    return dict(row)


def all_rows():
    """Return every transaction as a list of dicts, oldest first."""
    conn = _connect()
    rows = conn.execute("SELECT * FROM txns ORDER BY date ASC, id ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def month_total(month):
    """
    Sum of expenses for a given month, e.g. month_total("2026-06").
    Income is excluded from the total (it's a separate concern on the
    dashboard / total command).
    """
    conn = _connect()
    row = conn.execute(
        """SELECT COALESCE(SUM(amount), 0) AS total
           FROM txns
           WHERE type = 'expense' AND date LIKE ?""",
        (f"{month}%",),
    ).fetchone()
    conn.close()
    return row["total"]


def month_income(month):
    conn = _connect()
    row = conn.execute(
        """SELECT COALESCE(SUM(amount), 0) AS total
           FROM txns
           WHERE type = 'income' AND date LIKE ?""",
        (f"{month}%",),
    ).fetchone()
    conn.close()
    return row["total"]


def category_totals(month):
    """Dict of {category: total_spent} for expenses in a given month."""
    conn = _connect()
    rows = conn.execute(
        """SELECT category, COALESCE(SUM(amount), 0) AS total
           FROM txns
           WHERE type = 'expense' AND date LIKE ?
           GROUP BY category
           ORDER BY total DESC""",
        (f"{month}%",),
    ).fetchall()
    conn.close()
    return {r["category"]: r["total"] for r in rows}


if __name__ == "__main__":
    # quick smoke test
    import os

    if DB_PATH.exists():
        os.remove(DB_PATH)

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
