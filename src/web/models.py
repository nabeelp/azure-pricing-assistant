"""Web request/response models for Flask application."""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ChatRequest:
    """Incoming chat message request."""

    session_id: str
    message: str

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "ChatRequest":
        """Create from JSON request."""
        return cls(
            session_id=data.get("session_id", ""),
            message=data.get("message", ""),
        )


@dataclass
class ChatResponse:
    """Response to chat message."""

    response: str
    is_done: bool
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        result = {
            "response": self.response,
            "is_done": self.is_done,
        }
        if self.error:
            result["error"] = self.error
        return result


@dataclass
class ProposalResponse:
    """Response with generated proposal."""

    bom: str
    pricing: str
    proposal: str
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        if self.error:
            return {"error": self.error}
        return {
            "bom": self.bom,
            "pricing": self.pricing,
            "proposal": self.proposal,
        }
