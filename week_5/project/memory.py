"""
memory.py
=========
Handles persistent chat history for the agent, supporting multiple sessions
with timestamps and metadata (Week 3 Architecture).
"""
import json
import os
import uuid
import glob
from datetime import datetime, timezone

SESSIONS_DIR = ".agent/sessions"

def create_session() -> str:
    """Return a new 8-char hex session ID."""
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    return uuid.uuid4().hex[:8]

def save_history(session_id: str, messages: list, title: str = "Code Scout Task"):
    """Write session JSON to .agent/sessions/{id}.json with metadata wrapper."""
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    filepath = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    
    session_data = {
        "id": session_id,
        "title": title,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "messages": messages
    }
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(session_data, f, indent=2)

def load_history(session_id: str) -> list:
    """Load session dict and return JUST the messages list."""
    filepath = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    
    if not os.path.exists(filepath):
        return []
        
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("messages", [])

def clear_history(session_id: str):
    """Deletes the history file for the given session to start fresh."""
    filepath = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    if os.path.exists(filepath):
        os.remove(filepath)

def list_sessions() -> list[dict]:
    """Return sessions sorted by updated_at descending (newest first)."""
    if not os.path.exists(SESSIONS_DIR):
        return []
        
    sessions = []
    for filepath in glob.glob(os.path.join(SESSIONS_DIR, "*.json")):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                sessions.append({
                    "id": data.get("id"),
                    "title": data.get("title", "Untitled"),
                    "updated_at": data.get("updated_at")
                })
        except Exception:
            continue
            
    return sorted(sessions, key=lambda x: x["updated_at"], reverse=True)