import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# Directory that holds this file (the backend/ folder).
BASE_DIR = Path(__file__).resolve().parent

# Load backend/.env so DATABASE_PATH (and anything else) actually takes effect.
load_dotenv(BASE_DIR / ".env")


def _resolve_db_path() -> str:
    """Resolve the SQLite path, anchoring relative paths to backend/."""
    raw = os.getenv("DATABASE_PATH", "chainguard.db")
    path = Path(raw)
    if not path.is_absolute():
        path = BASE_DIR / path
    return str(path)


DB_NAME = _resolve_db_path()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_conn():
    """Open a connection, commit on success, always close it."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS disruptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT,
            payload TEXT
        );

        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT,
            disruption_id INTEGER,
            payload TEXT,
            status TEXT DEFAULT 'pending'
        );

        CREATE TABLE IF NOT EXISTS approvals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT,
            analysis_id INTEGER,
            status TEXT DEFAULT 'pending',
            reviewer TEXT,
            comments TEXT,
            decided_at TEXT
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT,
            event_type TEXT,
            actor TEXT,
            details TEXT
        );
        """)


def add_record(table, columns, values):
    placeholders = ",".join("?" for _ in values)
    with get_conn() as conn:
        cursor = conn.execute(
            f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
            values,
        )
        return cursor.lastrowid


def get_record(table, record_id):
    with get_conn() as conn:
        row = conn.execute(
            f"SELECT * FROM {table} WHERE id = ?",
            (record_id,),
        ).fetchone()
        return dict(row) if row else None


def list_records(table, limit=100, offset=0):
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM {table} ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [dict(row) for row in rows]


def count_records(table) -> int:
    """Exact row count, independent of any list limit."""
    with get_conn() as conn:
        row = conn.execute(
            f"SELECT COUNT(*) AS c FROM {table}"
        ).fetchone()
        return int(row["c"])


def decide_approval(approval_id, status, reviewer, comments) -> bool:
    """Record a decision atomically. Returns False if it was already decided."""
    with get_conn() as conn:
        cursor = conn.execute(
            """
            UPDATE approvals
            SET status=?, reviewer=?, comments=?, decided_at=?
            WHERE id=? AND status='pending'
            """,
            (status, reviewer, comments, now(), approval_id),
        )
        if cursor.rowcount == 0:
            return False

        row = conn.execute(
            "SELECT analysis_id FROM approvals WHERE id = ?",
            (approval_id,),
        ).fetchone()

        if row and row["analysis_id"] is not None:
            conn.execute(
                "UPDATE analyses SET status=? WHERE id=?",
                (status, row["analysis_id"]),
            )
        return True


def log_event(event_type, actor, details):
    add_record(
        "audit_logs",
        "created_at, event_type, actor, details",
        (now(), event_type, actor, json.dumps(details)),
    )
