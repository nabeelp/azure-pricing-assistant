"""HTTP route handlers for Web API."""

import asyncio
import logging
import os
from typing import Any, Dict

from src.web.interface import WebInterface
from src.web.models import ChatResponse, ProposalResponse
from src.shared.metrics import increment_chat_turns, increment_proposals_generated, increment_errors

# Get logger (setup handled by application entry point)
logger = logging.getLogger(__name__)


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
            Dictionary with response, is_done, requirements_summary, bom_items, and optional error
        """
        logger.debug(f"Processing chat for session {session_id}, message length: {len(message)}")
        
        try:
            # Increment chat turns metric
            increment_chat_turns(session_id)
            
            result = await self.interface.chat_turn(session_id, message)

            # Filter out JSON blocks from the response display
            response = result.get("response") or ""
            if response.strip().startswith("{"):
                # This is likely the JSON completion message - don't show it
                response = ""

            return {
                "response": response,
                "is_done": result.get("is_done", False),
                "requirements_summary": result.get("requirements_summary"),
                "bom_items": result.get("bom_items", []),
                "bom_updated": result.get("bom_updated", False),
                "error": result.get("error"),
            }
        except Exception as e:
            logger.error(f"Error in chat handler: {e}")
            increment_errors("chat_error", session_id)
            raise

    async def handle_generate_proposal(self, session_id: str) -> Dict[str, Any]:
        """
        Handle proposal generation endpoint.

        Args:
            session_id: Unique session identifier

        Returns:
            Dictionary with bom, pricing, proposal, or error
        """
        try:
            result = await self.interface.generate_proposal(session_id)

            if "error" in result:
                increment_errors("proposal_error", session_id)
                increment_proposals_generated(session_id, success=False)
                return {"error": result["error"]}

            # Increment successful proposal generation metric
            increment_proposals_generated(session_id, success=True)

            return {
                "bom": result.get("bom", ""),
                "pricing": result.get("pricing", ""),
                "proposal": result.get("proposal", ""),
            }
        except Exception as e:
            logger.error(f"Error in proposal generation handler: {e}")
            increment_errors("proposal_error", session_id)
            increment_proposals_generated(session_id, success=False)
            raise

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
            logger.warning(f"No session data found for streaming proposal: {session_id}")
            increment_errors("no_session", session_id)
            yield {"error": "No active session found"}
            return

        try:
            # Get requirements from history
            requirements = history_to_requirements(session_data.history)
            logger.info(f"Starting proposal stream for session {session_id}")

            # Stream workflow events
            async with self.interface.context as ctx:
                async for event in run_bom_pricing_proposal_stream(ctx.client, requirements):
                    yield {
                        "event_type": event.event_type,
                        "agent_name": event.agent_name,
                        "message": event.message,
                        "data": event.data,
                    }
            
            # Increment successful proposal generation metric
            increment_proposals_generated(session_id, success=True)
            
        except Exception as e:
            logger.error(f"Error in proposal stream for session {session_id}: {e}")
            increment_errors("proposal_stream_error", session_id)
            increment_proposals_generated(session_id, success=False)
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

    async def handle_get_bom(self, session_id: str) -> Dict[str, Any]:
        """
        Handle BOM retrieval endpoint.

        Args:
            session_id: Unique session identifier

        Returns:
            Dictionary with:
                - bom_items: List of BOM items
                - bom_task_status: Current task status (idle, queued, processing, complete, error)
                - bom_last_update: ISO 8601 timestamp of last BOM modification
                - bom_task_error: Error message if status is error
        """
        return await self.interface.get_bom_items(session_id)

    def handle_get_proposal(self, session_id: str) -> Dict[str, Any]:
        """
        Handle proposal retrieval endpoint.

        Args:
            session_id: Unique session identifier

        Returns:
            Dictionary with stored proposal (bom, pricing, proposal) or error
        """
        return self.interface.get_stored_proposal(session_id)

    def handle_get_all_proposals(self) -> Dict[str, Any]:
        """
        Handle retrieval of all proposals across all sessions.

        Returns:
            Dictionary with proposals array containing session_id and proposal data
        """
        try:
            sessions_with_proposals = self.interface.context.session_store.get_all_with_proposals()
            
            proposals = []
            for session_id, session_data in sessions_with_proposals.items():
                if session_data.proposal:
                    proposals.append({
                        "session_id": session_id,
                        "bom": session_data.proposal.bom_text,
                        "pricing": session_data.proposal.pricing_text,
                        "proposal": session_data.proposal.proposal_text,
                    })
            
            return {"proposals": proposals, "count": len(proposals)}
        except Exception as e:
            logger.error(f"Error retrieving all proposals: {e}")
            return {"error": str(e), "proposals": [], "count": 0}
