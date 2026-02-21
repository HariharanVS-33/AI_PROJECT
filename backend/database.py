"""
SQLite database setup and helpers.
Tables: sessions, messages, leads
"""
import sqlite3
import json
import os
from datetime import datetime
from backend.config import SQLITE_DB_PATH


def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(SQLITE_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(SQLITE_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id   TEXT PRIMARY KEY,
            created_at   TEXT NOT NULL,
            last_active  TEXT NOT NULL,
            lead_status  TEXT NOT NULL DEFAULT 'NOT_STARTED',
            lead_data    TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS messages (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id   TEXT NOT NULL,
            role         TEXT NOT NULL,
            content      TEXT NOT NULL,
            intent       TEXT,
            created_at   TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );

        CREATE TABLE IF NOT EXISTS leads (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id          TEXT NOT NULL,
            first_name          TEXT,
            last_name           TEXT,
            email               TEXT,
            company_name        TEXT,
            job_title           TEXT,
            territory           TEXT,
            product_interest    TEXT,
            monthly_volume      TEXT,
            phone               TEXT,
            hubspot_contact_id  TEXT,
            hubspot_company_id  TEXT,
            created_at          TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()
    print("✅ Database initialised")


def save_message(session_id: str, role: str, content: str, intent: str = None) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO messages (session_id, role, content, intent, created_at) VALUES (?, ?, ?, ?, ?)",
        (session_id, role, content, intent, datetime.utcnow().isoformat()),
    )
    conn.execute(
        "UPDATE sessions SET last_active = ? WHERE session_id = ?",
        (datetime.utcnow().isoformat(), session_id),
    )
    conn.commit()
    conn.close()


def save_lead(session_id: str, lead_data: dict, hubspot_ids: dict = None) -> None:
    hubspot_ids = hubspot_ids or {}
    conn = get_connection()
    conn.execute(
        """INSERT INTO leads
           (session_id, first_name, last_name, email, company_name, job_title,
            territory, product_interest, monthly_volume, phone,
            hubspot_contact_id, hubspot_company_id, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            session_id,
            lead_data.get("first_name"),
            lead_data.get("last_name"),
            lead_data.get("email"),
            lead_data.get("company_name"),
            lead_data.get("job_title"),
            lead_data.get("territory"),
            lead_data.get("product_interest"),
            lead_data.get("monthly_volume"),
            lead_data.get("phone"),
            hubspot_ids.get("contact_id"),
            hubspot_ids.get("company_id"),
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    conn.close()
