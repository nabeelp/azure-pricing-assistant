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

    async def handle_generate_proposal_stream(self, session_id: str):
        """
        Handle proposal generation with streaming progress.
        
        Args:
            session_id: Unique session identifier
            
        Yields:
            Dict[str, Any] - Progress events
        """
        from src.core.orchestrator import history_to_requirements, run_bom_pricing_proposal_stream
        
        # Get session data
        session_data = self.interface.context.session_store.get(session_id)
        if not session_data:
            yield {"error": "No active session found"}
            return
        
        try:
            # Get requirements from history
            requirements = history_to_requirements(session_data.history)
            
            # Stream workflow events
            async with self.interface.context as ctx:
                async for event in run_bom_pricing_proposal_stream(ctx.client, requirements):
                    yield {
                        "event_type": event.event_type,
                        "agent_name": event.agent_name,
                        "message": event.message,
                        "data": event.data
                    }
        except Exception as e:
            yield {"error": str(e)}

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
