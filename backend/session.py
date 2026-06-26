"""
Session management for PanoSync.
Stores session data as JSON files in data/sessions/
"""

import json
import uuid
from pathlib import Path
from typing import Optional

from . import storage


def new_session_id() -> str:
    """Generate a new unique session ID."""
    return str(uuid.uuid4())


def get_session_path(session_id: str) -> Path:
    """Get the file path for a session."""
    return storage.sessions_dir() / f"{session_id}.json"


def save_session(session_id: str, data: dict) -> None:
    """Save session data to disk."""
    path = get_session_path(session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def load_session(session_id: str) -> Optional[dict]:
    """Load session data from disk. Returns None if not found."""
    path = get_session_path(session_id)
    if not path.exists():
        return None

    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def update_session(session_id: str, updates: dict) -> None:
    """Update session data with new fields."""
    session = load_session(session_id)
    if session is None:
        session = {}

    session.update(updates)
    save_session(session_id, session)


def delete_session(session_id: str) -> bool:
    """Delete a session. Returns True if deleted, False if not found."""
    path = get_session_path(session_id)
    if path.exists():
        path.unlink()
        return True
    return False
