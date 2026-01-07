"""HTTP route handlers for Web API."""

import asyncio
import os
from typing import Any, Dict

from src.web.interface import WebInterface
from src.web.models import ChatResponse, ProposalResponse


class WebHandlers:
    """Handlers for Web API endpoints."""

    def __init__(self, web_interface: WebInterface):
        """
        Initialize handlers.

        Args:
            web_interface: WebInterface instance for handling requests
        """
        self.interface = web_interface

    async def handle_chat(self, session_id: str, message: str) -> Dict[str, Any]:
        """
        Handle chat endpoint.

        Args:
            session_id: Unique session identifier
            message: User message

        Returns:
            Dictionary with response, is_done, and optional error
        """
        result = await self.interface.chat_turn(session_id, message)

        return {
            "response": result.get("response", ""),
            "is_done": result.get("is_done", False),
            "error": result.get("error"),
        }

    async def handle_generate_proposal(self, session_id: str) -> Dict[str, Any]:
        """
        Handle proposal generation endpoint.

        Args:
            session_id: Unique session identifier

        Returns:
            Dictionary with bom, pricing, proposal, or error
        """
        result = await self.interface.generate_proposal(session_id)

        if "error" in result:
            return {"error": result["error"]}

        return {
            "bom": result.get("bom", ""),
            "pricing": result.get("pricing", ""),
            "proposal": result.get("proposal", ""),
        }

    async def handle_reset(self, session_id: str) -> Dict[str, str]:
        """
        Handle reset endpoint.

        Args:
            session_id: Unique session identifier

        Returns:
            Dictionary with status
        """
        await self.interface.reset_session(session_id)
        return {"status": "reset"}

    async def handle_history(self, session_id: str) -> Dict[str, Any]:
        """
        Handle history retrieval endpoint.

        Args:
            session_id: Unique session identifier

        Returns:
            Dictionary with history or error
        """
        history = await self.interface.get_session_history(session_id)
        return {"history": history}
