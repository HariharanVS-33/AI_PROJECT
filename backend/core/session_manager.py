"""
In-memory session manager with SQLite persistence.
"""
import uuid
import logging
from datetime import datetime, timedelta
from backend.config import SESSION_EXPIRY_MINUTES
from backend import database as db

logger = logging.getLogger(__name__)

# In-memory session store: {session_id: session_dict}
_sessions: dict = {}


def create_session() -> str:
    """Create a new session and persist it to SQLite."""
    session_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    session = {
        "session_id": session_id,
        "history": [],           # [{"role": "user"|"model", "parts": [text]}]
        "lead_status": "NOT_STARTED",
        "lead_data": {},
        "current_field_index": 0,
        "created_at": now,
        "last_active": now,
    }
    _sessions[session_id] = session

    # Persist to SQLite
    conn = db.get_connection()
    conn.execute(
        "INSERT INTO sessions (session_id, created_at, last_active, lead_status, lead_data) "
        "VALUES (?, ?, ?, ?, ?)",
        (session_id, now, now, "NOT_STARTED", "{}"),
    )
    conn.commit()
    conn.close()

    logger.info(f"Session created: {session_id}")
    return session_id


def get_session(session_id: str) -> dict | None:
    """Return session dict or None if not found / expired."""
    session = _sessions.get(session_id)
    if not session:
        return None

    # Check expiry
    last_active = datetime.fromisoformat(session["last_active"])
    if datetime.utcnow() - last_active > timedelta(minutes=SESSION_EXPIRY_MINUTES):
        del _sessions[session_id]
        logger.info(f"Session expired: {session_id}")
        return None

    return session


def update_session_activity(session_id: str) -> None:
    session = _sessions.get(session_id)
    if session:
        session["last_active"] = datetime.utcnow().isoformat()


def add_to_history(session: dict, role: str, text: str) -> None:
    """Add a message to the in-memory conversation history."""
    session["history"].append({"role": role, "parts": [text]})
    # Keep only last 20 turns (10 exchanges) to manage context length
    if len(session["history"]) > 20:
        session["history"] = session["history"][-20:]
