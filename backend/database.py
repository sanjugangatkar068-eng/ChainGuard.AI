
import sqlite3
import json
from datetime import datetime, timezone

DB_NAME = "chainguard.db"


def now():
    return datetime.now(timezone.utc).isoformat()


def init_db():
    with sqlite3.connect(DB_NAME) as conn:
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
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute(
            f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
            values
        )
        return cursor.lastrowid


def get_record(table, record_id):
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            f"SELECT * FROM {table} WHERE id = ?",
            (record_id,)
        ).fetchone()
        return dict(row) if row else None


def list_records(table, limit=100):
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"SELECT * FROM {table} ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(row) for row in rows]


def log_event(event_type, actor, details):
    add_record(
        "audit_logs",
        "created_at, event_type, actor, details",
        (now(), event_type, actor, json.dumps(details))
    )
