"""Web interface implementation for Azure Pricing Assistant."""

import logging
from typing import Any, Dict

from src.interfaces.base import PricingInterface
from src.interfaces.context import InterfaceContext
from src.interfaces.handlers import WorkflowHandler

# Get logger (setup handled by application entry point)
logger = logging.getLogger(__name__)


class WebInterface(PricingInterface):
    """Web interface implementation for Flask application."""

    def __init__(self, session_store=None):
        """
        Initialize Web interface.

        Args:
            session_store: Optional custom session store (defaults to InMemorySessionStore)
        """
        self.context = InterfaceContext(session_store)
        self.handler = WorkflowHandler()

    async def chat_turn(self, session_id: str, message: str) -> Dict[str, Any]:
        """
        Process a single chat turn for Web API.

        Args:
            session_id: Unique identifier for the chat session
            message: User's input message

        Returns:
            JSON-compatible dictionary with response, is_done, and history
        """
        async with self.context as ctx:
            result = await self.handler.handle_chat_turn(ctx, session_id, message)
            
            # Log BOM updates for debugging (data is returned via handle_chat in handlers.py)
            if result.get("bom_updated"):
                bom_count = len(result.get("bom_items", []))
                logger.debug(f"Session {session_id}: BOM updated, {bom_count} items")
            
            # Remove history from web responses (optional - only if needed for bandwidth)
            return {
                "response": result.get("response", ""),
                "is_done": result.get("is_done", False),
                "error": result.get("error"),
            }

    async def generate_proposal(self, session_id: str) -> Dict[str, Any]:
        """
        Generate proposal for Web API.

        Args:
            session_id: Unique identifier for the chat session

        Returns:
            JSON-compatible dictionary with bom, pricing, and proposal text
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

    async def get_bom_items(self, session_id: str) -> list:
        """
        Get current BOM items for a session.

        Args:
            session_id: Unique identifier for the chat session

        Returns:
            List of BOM items
        """
        session_data = self.context.session_store.get(session_id)
        if not session_data:
            return []
        return session_data.bom_items or []
