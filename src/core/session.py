"""Session storage abstractions for chat threads."""

from typing import Dict, Optional

from .models import SessionData


class InMemorySessionStore:
    """Lightweight in-memory session store (dev use only)."""

    def __init__(self) -> None:
        self._sessions: Dict[str, SessionData] = {}

    def get(self, session_id: str) -> Optional[SessionData]:
        return self._sessions.get(session_id)

    def set(self, session_id: str, data: SessionData) -> None:
        self._sessions[session_id] = data

    def delete(self, session_id: str) -> None:
        if session_id in self._sessions:
            del self._sessions[session_id]

    def clear(self) -> None:
        self._sessions.clear()
