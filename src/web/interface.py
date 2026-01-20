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
            JSON-compatible dictionary with response, is_done, BOM fields, and errors
        """
        async with self.context as ctx:
            result = await self.handler.handle_chat_turn(
                ctx, session_id, message, run_bom_in_background=False
            )
            
            # Log BOM updates for debugging (data is returned via handle_chat in handlers.py)
            if result.get("bom_updated"):
                bom_count = len(result.get("bom_items", []))
                logger.debug(f"Session {session_id}: BOM updated, {bom_count} items")
            
            # Include pricing information in response
            session_data = self.context.session_store.get(session_id)
            pricing_info = {}
            if session_data:
                pricing_info = {
                    "pricing_items": session_data.pricing_items or [],
                    "pricing_total": session_data.pricing_total,
                    "pricing_currency": session_data.pricing_currency,
                    "pricing_date": session_data.pricing_date,
                    "pricing_task_status": session_data.pricing_task_status,
                    "pricing_task_error": session_data.pricing_task_error,
                }
            
            # Remove history from web responses (optional - only if needed for bandwidth)
            return {
                "response": result.get("response", ""),
                "is_done": result.get("is_done", False),
                "requirements_summary": result.get("requirements_summary"),
                "bom_items": result.get("bom_items", []),
                "bom_updated": result.get("bom_updated", False),
                "bom_task_status": result.get("bom_task_status"),
                "bom_task_error": result.get("bom_task_error"),
                **pricing_info,  # Include pricing info
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
        await self.handler.handle_reset_session(self.context, session_id)

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

    async def get_bom_items(self, session_id: str) -> Dict[str, Any]:
        """
        Get current BOM items and task status for a session.

        Args:
            session_id: Unique identifier for the chat session

        Returns:
            Dictionary with:
                - bom_items: List of BOM items
                - bom_task_status: Current task status (idle, queued, processing, complete, error)
                - bom_last_update: ISO 8601 timestamp of last BOM modification (or None)
                - bom_task_error: Error message if status is error (or None)
        """
        session_data = self.context.session_store.get(session_id)
        if not session_data:
            return {
                "bom_items": [],
                "bom_task_status": "idle",
                "bom_last_update": None,
                "bom_task_error": None
            }
        
        # Format bom_last_update as ISO 8601 string if present
        last_update_str = None
        if session_data.bom_last_update:
            last_update_str = session_data.bom_last_update.isoformat()
        
        return {
            "bom_items": session_data.bom_items or [],
            "bom_task_status": session_data.bom_task_status,
            "bom_last_update": last_update_str,
            "bom_task_error": session_data.bom_task_error
        }

    async def get_pricing_items(self, session_id: str) -> Dict[str, Any]:
        """
        Get current pricing items and task status for a session.

        Args:
            session_id: Unique identifier for the chat session

        Returns:
            Dictionary with:
                - pricing_items: List of pricing items
                - pricing_total: Cumulative total monthly cost
                - pricing_currency: Currency code (e.g., "USD")
                - pricing_date: ISO 8601 date of pricing data
                - pricing_task_status: Current task status (idle, queued, processing, complete, error)
                - pricing_last_update: ISO 8601 timestamp of last pricing modification (or None)
                - pricing_task_error: Error message if status is error (or None)
        """
        session_data = self.context.session_store.get(session_id)
        if not session_data:
            return {
                "pricing_items": [],
                "pricing_total": 0.0,
                "pricing_currency": "USD",
                "pricing_date": None,
                "pricing_task_status": "idle",
                "pricing_last_update": None,
                "pricing_task_error": None
            }
        
        # Format pricing_last_update as ISO 8601 string if present
        last_update_str = None
        if session_data.pricing_last_update:
            last_update_str = session_data.pricing_last_update.isoformat()
        
        return {
            "pricing_items": session_data.pricing_items or [],
            "pricing_total": session_data.pricing_total,
            "pricing_currency": session_data.pricing_currency,
            "pricing_date": session_data.pricing_date,
            "pricing_task_status": session_data.pricing_task_status,
            "pricing_last_update": last_update_str,
            "pricing_task_error": session_data.pricing_task_error
        }

    def get_stored_proposal(self, session_id: str) -> Dict[str, Any]:
        """
        Get stored proposal for a session.

        Args:
            session_id: Unique identifier for the chat session

        Returns:
            Dictionary with bom, pricing, proposal, or error
        """
        return self.handler.get_stored_proposal(self.context, session_id)
