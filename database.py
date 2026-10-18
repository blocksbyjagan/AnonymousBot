
import json
import os
import secrets
import sqlite3
import string
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "device_lab.db")


def get_connection():
    connection = sqlite3.connect(DB_NAME, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def create_database():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_user_id INTEGER PRIMARY KEY,
                visitor_id TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                visitor_id TEXT NOT NULL,
                report_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_reports_owner
            ON reports (telegram_user_id, id)
        """)


def get_visitor_id(telegram_user_id):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT visitor_id FROM users WHERE telegram_user_id = ?",
            (telegram_user_id,)
        ).fetchone()

    return row["visitor_id"] if row else None


def get_or_create_visitor_id(telegram_user_id):
    existing = get_visitor_id(telegram_user_id)

    if existing:
        return existing

    characters = string.ascii_uppercase + string.digits

    for _ in range(10):
        visitor_id = "".join(
            secrets.choice(characters) for _ in range(8)
        )

        try:
            with get_connection() as connection:
                connection.execute(
                    """
                    INSERT INTO users
                    (telegram_user_id, visitor_id, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (
                        telegram_user_id,
                        visitor_id,
                        datetime.now(timezone.utc).isoformat()
                    )
                )

            return visitor_id

        except sqlite3.IntegrityError:
            existing = get_visitor_id(telegram_user_id)

            if existing:
                return existing

    raise RuntimeError("Could not create a unique visitor ID")


def get_telegram_user_id(visitor_id):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT telegram_user_id FROM users WHERE visitor_id = ?",
            (visitor_id,)
        ).fetchone()

    return row["telegram_user_id"] if row else None


def save_report(telegram_user_id, visitor_id, report):
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO reports
            (telegram_user_id, visitor_id, report_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                telegram_user_id,
                visitor_id,
                json.dumps(report),
                datetime.now(timezone.utc).isoformat()
            )
        )

        return cursor.lastrowid


def get_reports(telegram_user_id, limit=5):
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, visitor_id, report_json, created_at
            FROM reports
            WHERE telegram_user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (telegram_user_id, limit)
        ).fetchall()

    return [
        {
            "id": row["id"],
            "visitor_id": row["visitor_id"],
            "report": json.loads(row["report_json"]),
            "created_at": row["created_at"]
        }
        for row in rows
    ]


create_database()
