"""Shared workflow handlers for both CLI and Web interfaces."""

import logging
from typing import Any, Dict

from src.core.orchestrator import (
    history_to_requirements,
    reset_session,
    run_bom_pricing_proposal,
    run_question_turn,
)
from src.core.models import ProposalBundle
from src.shared.errors import WorkflowError
from .context import InterfaceContext

# Get logger (setup handled by application entry point)
logger = logging.getLogger(__name__)


class WorkflowHandler:
    """
    Centralized handler for workflow operations used by all interfaces.
    
    Eliminates code duplication by providing a single implementation
    for chat turns, proposal generation, and session management.
    """

    async def handle_chat_turn(
        self,
        context: InterfaceContext,
        session_id: str,
        message: str,
    ) -> Dict[str, Any]:
        """
        Process a single chat turn with the Question Agent.

        This is the shared implementation used by both CLI and Web interfaces.

        Args:
            context: InterfaceContext with initialized client and session store
            session_id: Unique identifier for the chat session
            message: User's input message

        Returns:
            Dictionary with:
                - 'response': Agent's response text
                - 'is_done': Whether requirements gathering is complete
                - 'history': Full chat history
        """
        if not context.validate():
            logger.error("Context not properly initialized for chat turn")
            return {
                "error": "Context not properly initialized",
                "response": "",
                "is_done": False,
            }

        try:
            result = await run_question_turn(
                context.client,
                context.session_store,
                session_id,
                message,
            )
            logger.debug(
                f"Chat turn complete for {session_id}: is_done={result.get('is_done')}"
            )
            return result
        except WorkflowError as e:
            # Turn limit reached - trigger proposal generation UI
            if "Maximum conversation turns" in str(e):
                return {
                    "response": str(e),
                    "error": str(e),
                    "is_done": True,
                }
            raise
        except Exception as e:
            return {
                "error": str(e),
                "response": f"Error: {str(e)}",
                "is_done": False,
            }

    async def handle_proposal_generation(
        self,
        context: InterfaceContext,
        session_id: str,
    ) -> Dict[str, Any]:
        """
        Generate BOM, pricing, and proposal from gathered requirements.

        This is the shared implementation used by both CLI and Web interfaces.

        Args:
            context: InterfaceContext with initialized client and session store
            session_id: Unique identifier for the chat session

        Returns:
            Dictionary with:
                - 'bom': Bill of Materials text
                - 'pricing': Pricing calculation text
                - 'proposal': Professional proposal Markdown
                - 'error': Error message if applicable
        """
        if not context.validate():
            logger.error("Context not properly initialized for proposal generation")
            return {"error": "Context not properly initialized"}

        session_data = context.session_store.get(session_id)
        if not session_data:
            logger.warning(f"No session data found for proposal generation: {session_id}")
            return {"error": "No active session found"}

        try:
            requirements = history_to_requirements(session_data.history)
            logger.info(f"Generating proposal for session {session_id}")

            bundle: ProposalBundle = await run_bom_pricing_proposal(
                context.client, requirements
            )
            
            logger.info(
                f"Proposal generated for session {session_id}: "
                f"BOM={len(bundle.bom_text)} chars, "
                f"Pricing={len(bundle.pricing_text)} chars, "
                f"Proposal={len(bundle.proposal_text)} chars"
            )

            return {
                "bom": bundle.bom_text,
                "pricing": bundle.pricing_text,
                "proposal": bundle.proposal_text,
            }
        except Exception as e:
            logger.error(f"Error generating proposal for session {session_id}: {e}")
            return {"error": str(e)}

    def handle_reset_session(
        self,
        context: InterfaceContext,
        session_id: str,
    ) -> Dict[str, str]:
        """
        Reset session state.

        Args:
            context: InterfaceContext with session store
            session_id: Unique identifier for the chat session

        Returns:
            Dictionary with status
        """
        reset_session(context.session_store, session_id)
        return {"status": "reset"}

    def get_session_history(
        self,
        context: InterfaceContext,
        session_id: str,
    ) -> Dict[str, Any]:
        """
        Get chat history for a session.

        Args:
            context: InterfaceContext with session store
            session_id: Unique identifier for the chat session

        Returns:
            Dictionary with:
                - 'history': List of chat messages
                - 'error': Error message if applicable
        """
        session_data = context.session_store.get(session_id)
        if not session_data:
            return {"error": "Session not found", "history": []}

        return {"history": session_data.history}
