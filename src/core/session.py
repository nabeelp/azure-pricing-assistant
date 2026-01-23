"""Session storage abstractions for chat threads."""

from typing import Dict, Optional

from .models import SessionData


class InMemorySessionStore:
    """Lightweight in-memory session store (dev use only)."""

    def __init__(self) -> None:
        """Initialize the in-memory session dictionary."""
        self._sessions: Dict[str, SessionData] = {}

    def get(self, session_id: str) -> Optional[SessionData]:
        """Return session data for a session id, if present."""
        return self._sessions.get(session_id)

    def set(self, session_id: str, data: SessionData) -> None:
        """Persist session data for the given session id."""
        self._sessions[session_id] = data

    def delete(self, session_id: str) -> None:
        """Remove a session if it exists in the store."""
        if session_id in self._sessions:
            del self._sessions[session_id]

    def clear(self) -> None:
        """Remove all sessions from the store."""
        self._sessions.clear()

    def get_all_with_proposals(self) -> Dict[str, SessionData]:
        """Get all sessions that have stored proposals.
        
        Returns:
            Dictionary mapping session_id to SessionData for sessions with proposals
        """
        return {sid: data for sid, data in self._sessions.items() if data.proposal is not None}
