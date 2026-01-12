"""Shared workflow handlers for both CLI and Web interfaces."""

import logging
from typing import Any, Dict, Optional

from opentelemetry.trace import SpanKind

from agent_framework.observability import get_tracer

from src.core.orchestrator import (
    history_to_requirements,
    reset_session,
    run_bom_pricing_proposal,
    run_question_turn,
)
from src.core.models import ProposalBundle
from src.shared.errors import WorkflowError
from src.web.session_tracing import end_session_span
from .context import InterfaceContext

# Get logger (setup handled by application entry point)
logger = logging.getLogger(__name__)


def _handler_span(operation: str, *, session_id: Optional[str] = None, **attrs: Any):
    """Create a span for handler operations with session and operation context.

    Args:
        operation: Name of the handler operation (e.g., "chat_turn", "proposal_generation")
        session_id: Optional session identifier for correlation
        **attrs: Additional span attributes

    Returns:
        Context manager for the span
    """
    tracer = get_tracer(instrumenting_module_name="azure_pricing_assistant.handlers")
    attributes: Dict[str, Any] = {
        "handler.operation": operation,
        **attrs,
    }
    if session_id:
        attributes["session.id"] = session_id
    return tracer.start_as_current_span(
        name=f"handler.{operation}",
        kind=SpanKind.INTERNAL,
        attributes=attributes,
    )


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
        with _handler_span(
            "chat_turn",
            session_id=session_id,
            message_length=len(message or ""),
        ):
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
        with _handler_span("proposal_generation", session_id=session_id):
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

                # Store proposal in session for retrieval
                session_data.proposal = bundle
                context.session_store.set(session_id, session_data)
                logger.debug(f"Proposal stored in session {session_id}")

                # End session span after successful proposal generation
                end_session_span(session_id)
                logger.debug(f"Session span ended for {session_id}")

                return {
                    "bom": bundle.bom_text,
                    "pricing": bundle.pricing_text,
                    "proposal": bundle.proposal_text,
                }
            except Exception as e:
                logger.error(f"Error generating proposal for session {session_id}: {e}")
                # End session span even on error to avoid orphaned spans
                end_session_span(session_id)
                return {"error": str(e)}

    async def handle_reset_session(
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
        await reset_session(context.session_store, session_id)
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

    def get_stored_proposal(
        self,
        context: InterfaceContext,
        session_id: str,
    ) -> Dict[str, Any]:
        """
        Get stored proposal for a session.

        Args:
            context: InterfaceContext with session store
            session_id: Unique identifier for the chat session

        Returns:
            Dictionary with:
                - 'bom': Bill of Materials text
                - 'pricing': Pricing calculation text
                - 'proposal': Professional proposal Markdown
                - 'error': Error message if no proposal found
        """
        session_data = context.session_store.get(session_id)
        if not session_data:
            return {"error": "Session not found"}

        if not session_data.proposal:
            return {"error": "No proposal found for this session"}

        return {
            "bom": session_data.proposal.bom_text,
            "pricing": session_data.proposal.pricing_text,
            "proposal": session_data.proposal.proposal_text,
        }
