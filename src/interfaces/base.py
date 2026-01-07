"""Abstract base class for interface implementations."""

from abc import ABC, abstractmethod
from typing import Any, Dict

from src.core.models import ProposalBundle


class PricingInterface(ABC):
    """Abstract base for different interface implementations (CLI, Web, API, etc.)."""

    @abstractmethod
    async def chat_turn(self, session_id: str, message: str) -> Dict[str, Any]:
        """
        Process a single chat turn with the Question Agent.

        Args:
            session_id: Unique identifier for the chat session
            message: User's input message

        Returns:
            Dictionary with keys:
                - 'response': Agent's response text
                - 'is_done': Boolean indicating if requirements gathering is complete
                - 'history': Full chat history (optional, implementation-specific)
                - 'error': Error message if applicable
        """
        pass

    @abstractmethod
    async def generate_proposal(self, session_id: str) -> Dict[str, Any]:
        """
        Generate BOM, pricing, and proposal from gathered requirements.

        Args:
            session_id: Unique identifier for the chat session

        Returns:
            Dictionary with keys:
                - 'bom': Bill of Materials text
                - 'pricing': Pricing calculation text
                - 'proposal': Professional proposal Markdown
                - 'error': Error message if applicable
        """
        pass

    @abstractmethod
    async def reset_session(self, session_id: str) -> None:
        """
        Reset session state, clearing chat history and requirements.

        Args:
            session_id: Unique identifier for the chat session
        """
        pass

    @abstractmethod
    async def get_session_history(self, session_id: str) -> list:
        """
        Get the chat history for a session.

        Args:
            session_id: Unique identifier for the chat session

        Returns:
            List of chat messages (dict with 'role' and 'content')
        """
        pass
