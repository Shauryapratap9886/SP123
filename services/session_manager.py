"""
Session and Context Management Service.
Maintains multi-turn conversation memory, active uploaded document context,
and metadata across follow-up queries.
"""

import time
import uuid
from typing import Dict, Any, List, Optional


class Session:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = time.time()
        self.last_activity = time.time()
        self.turns: List[Dict[str, Any]] = []
        self.active_document: Optional[Dict[str, Any]] = None

    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        self.last_activity = time.time()
        self.turns.append({
            "role": role,
            "content": content,
            "timestamp": time.time(),
            "metadata": metadata or {}
        })

    def set_document(self, doc_data: Dict[str, Any]):
        self.last_activity = time.time()
        self.active_document = doc_data

    def clear_document(self):
        self.active_document = None

    def get_conversation_history(self, max_turns: int = 8) -> List[Dict[str, Any]]:
        return self.turns[-max_turns:]

    def clear(self):
        self.turns = []
        self.active_document = None
        self.last_activity = time.time()


class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, Session] = {}

    def get_or_create(self, session_id: Optional[str] = None) -> Session:
        if not session_id or session_id not in self.sessions:
            new_id = session_id or str(uuid.uuid4())
            self.sessions[new_id] = Session(new_id)
            return self.sessions[new_id]
        
        session = self.sessions[session_id]
        session.last_activity = time.time()
        return session

    def cleanup_expired(self, max_idle_seconds: int = 7200):
        """Remove sessions idle for more than 2 hours."""
        now = time.time()
        expired = [sid for sid, s in self.sessions.items() if now - s.last_activity > max_idle_seconds]
        for sid in expired:
            del self.sessions[sid]


# Global singleton instance
session_manager = SessionManager()
