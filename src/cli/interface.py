"""CLI interface implementation for Azure Pricing Assistant."""

from typing import Any, Dict

from src.interfaces.base import PricingInterface
from src.interfaces.context import InterfaceContext
from src.interfaces.handlers import WorkflowHandler


class CLIInterface(PricingInterface):
    """Command-line interface implementation."""

    def __init__(self, session_store=None):
        """
        Initialize CLI interface.

        Args:
            session_store: Optional custom session store (defaults to InMemorySessionStore)
        """
        self.context = InterfaceContext(session_store)
        self.handler = WorkflowHandler()

    async def chat_turn(self, session_id: str, message: str) -> Dict[str, Any]:
        """
        Process a single chat turn.

        Args:
            session_id: Unique identifier for the chat session
            message: User's input message

        Returns:
            Dictionary with response, is_done, and history
        """
        async with self.context as ctx:
            return await self.handler.handle_chat_turn(ctx, session_id, message)

    async def generate_proposal(self, session_id: str) -> Dict[str, Any]:
        """
        Generate proposal from gathered requirements.

        Args:
            session_id: Unique identifier for the chat session

        Returns:
            Dictionary with bom, pricing, and proposal text
        """
        async with self.context as ctx:
            return await self.handler.handle_proposal_generation(ctx, session_id)

    async def reset_session(self, session_id: str) -> None:
        """
        Reset session state.

        Args:
            session_id: Unique identifier for the chat session
        """
        self.handler.handle_reset_session(self.context, session_id)

    async def get_session_history(self, session_id: str) -> list:
        """
        Get chat history for a session.

        Args:
            session_id: Unique identifier for the chat session

        Returns:
            List of chat messages
        """
        history_dict = self.handler.get_session_history(self.context, session_id)
        return history_dict.get("history", [])
