"""Shared orchestration helpers for CLI and web interfaces."""

import asyncio
import json
import logging
import re
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from opentelemetry.trace import SpanKind

from agent_framework import AgentRunUpdateEvent, ExecutorInvokedEvent, SequentialBuilder
from agent_framework.observability import get_tracer
from agent_framework_azure_ai import AzureAIAgentClient

from src.agents import (
    create_architect_agent,
    extract_partial_bom_from_response,
    create_pricing_agent,
    create_proposal_agent,
)
from src.agents.pricing_agent import parse_pricing_response
from src.shared.errors import WorkflowError
from src.shared.metrics import increment_errors
from .models import ProposalBundle, SessionData, PricingResult
from .session import InMemorySessionStore

# Configure logging
logger = logging.getLogger(__name__)


def _stage_span(stage_name: str, *, session_id: Optional[str] = None, **attrs: Any):
    """Create a traced span for a workflow stage with shared attributes."""
    tracer = get_tracer(instrumenting_module_name="azure_pricing_assistant.stages")
    attributes: Dict[str, Any] = {
        "workflow.stage": stage_name,
        **attrs,
    }
    if session_id:
        attributes["session.id"] = session_id
    return tracer.start_as_current_span(
        name=f"stage.{stage_name.lower().replace(' ', '_')}",
        kind=SpanKind.INTERNAL,
        attributes=attributes,
    )


async def _run_pricing_task_background(
    client: AzureAIAgentClient,
    session_store: InMemorySessionStore,
    session_id: str,
) -> None:
    """
    Background task wrapper for calculating incremental pricing.
    
    Handles state transitions and error handling for async pricing updates.
    Updates session state with task status and pricing results.
    
    Args:
        client: Azure AI Agent client
        session_store: Session store
        session_id: Session identifier
    """
    from src.agents.pricing_agent import calculate_incremental_pricing
    
    session_data = session_store.get(session_id)
    if not session_data:
        logger.warning(f"No session data found for {session_id} in pricing background task")
        return
    
    # Only price if we have BOM items
    if not session_data.bom_items:
        logger.info(f"No BOM items to price for session {session_id}")
        session_data.pricing_task_status = "idle"
        session_store.set(session_id, session_data)
        return
    
    # Transition to processing state
    session_data.pricing_task_status = "processing"
    session_data.pricing_task_error = None
    session_store.set(session_id, session_data)
    
    try:
        # Run pricing calculation with 30s timeout
        pricing_result = await asyncio.wait_for(
            calculate_incremental_pricing(client, session_data.bom_items),
            timeout=30.0
        )
        
        # Update session with pricing results
        session_data = session_store.get(session_id)
        if session_data:
            session_data.pricing_items = pricing_result.get("pricing_items", [])
            session_data.pricing_total = pricing_result.get("total_monthly", 0.0)
            session_data.pricing_currency = pricing_result.get("currency", "USD")
            session_data.pricing_date = pricing_result.get("pricing_date")
            session_data.pricing_task_status = "complete"
            session_data.pricing_last_update = datetime.now()
            
            # Log any errors from pricing
            errors = pricing_result.get("errors", [])
            if errors:
                logger.warning(f"Pricing errors for session {session_id}: {errors}")
                session_data.pricing_task_error = "; ".join(errors[:3])  # Show first 3 errors
            
            session_store.set(session_id, session_data)
            logger.info(f"Pricing task complete for session {session_id}: ${session_data.pricing_total:.2f}")
    
    except asyncio.TimeoutError:
        logger.error(f"Pricing task timeout for session {session_id}", exc_info=True)
        increment_errors("pricing_timeout", session_id=session_id)
        session_data = session_store.get(session_id)
        if session_data:
            session_data.pricing_task_status = "error"
            session_data.pricing_task_error = "Pricing calculation timed out after 30 seconds"
            session_store.set(session_id, session_data)
    
    except asyncio.CancelledError:
        logger.info(f"Pricing task cancelled for session {session_id}")
        session_data = session_store.get(session_id)
        if session_data:
            session_data.pricing_task_status = "idle"
            session_store.set(session_id, session_data)
        raise
    
    except Exception as e:
        # Log full traceback for debugging
        error_traceback = traceback.format_exc()
        logger.error(
            f"Pricing task error for session {session_id}: {e}\n{error_traceback}",
            exc_info=True,
            extra={"session_id": session_id, "error_type": type(e).__name__}
        )
        increment_errors("pricing_task_failure", session_id=session_id)
        
        session_data = session_store.get(session_id)
        if session_data:
            session_data.pricing_task_status = "error"
            # Sanitize error message for UI (no traceback)
            session_data.pricing_task_error = f"Pricing calculation failed: {str(e)}"
            session_store.set(session_id, session_data)


async def run_question_turn(
    client: AzureAIAgentClient,
    session_store: InMemorySessionStore,
    session_id: str,
    user_message: str,
) -> Dict[str, Any]:
    """Run a single architect-agent turn and persist thread/history.
    
    The architect agent progressively builds BOM items during conversation.

    Args:
        client: Azure AI Agent client
        session_store: Session store
        session_id: Session identifier
        user_message: User's message

    Returns:
        Dict with response, is_done, requirements_summary, history, and bom_items
    """
    with _stage_span(
        "Gathering requirements",
        session_id=session_id,
        message_length=len(user_message or ""),
    ):
        architect_agent = create_architect_agent(client)

        session_data = session_store.get(session_id)
        if not session_data:
            thread = architect_agent.get_new_thread()
            session_data = SessionData(thread=thread, history=[])
        else:
            thread = session_data.thread

        # Check turn limit before running
        if session_data.turn_count >= 20:
            raise WorkflowError(
                "Maximum conversation turns (20) reached. "
                "Please generate a proposal to continue with cost analysis."
            )

        response_text = ""
        async for update in architect_agent.run_stream(user_message, thread=thread):
            if update.text:
                response_text += update.text

        session_data.history.append({"role": "user", "content": user_message})
        session_data.history.append({"role": "assistant", "content": response_text})

        # Increment turn counter after successful run
        session_data.turn_count += 1

        # Extract partial BOM items from architect response
        partial_bom = extract_partial_bom_from_response(response_text)
        bom_updated = False
        if partial_bom:
            # Merge with existing BOM items
            existing_bom = session_data.bom_items or []
            session_data.bom_items = _merge_bom_items(existing_bom, partial_bom)
            bom_updated = True
            logger.info(f"Architect identified {len(partial_bom)} new/updated BOM items, total: {len(session_data.bom_items)}")
            
            # Trigger pricing calculation in background when BOM is updated
            if session_data.bom_items:
                # Cancel any existing pricing task
                if session_data.pricing_task_handle and not session_data.pricing_task_handle.done():
                    session_data.pricing_task_handle.cancel()
                
                # Queue pricing task
                session_data.pricing_task_status = "queued"
                session_data.pricing_task_error = None
                session_store.set(session_id, session_data)
                
                # Start pricing task in background
                pricing_task = asyncio.create_task(
                    _run_pricing_task_background(client, session_store, session_id)
                )
                session_data.pricing_task_handle = pricing_task
                logger.info(f"Started background pricing task for session {session_id}")
        
        session_store.set(session_id, session_data)

        is_done, requirements_summary = parse_question_completion(response_text)

        result = {
            "response": response_text,
            "is_done": is_done,
            "requirements_summary": requirements_summary,
            "history": session_data.history,
            "bom_items": session_data.bom_items or [],
            "bom_updated": bom_updated,
        }

        return result


def history_to_requirements(history: List[Dict[str, str]]) -> str:
    """Derive requirements from history, preferring the final completion payload."""
    for msg in reversed(history):
        if msg.get("role") != "assistant":
            continue

        is_done, requirements = parse_question_completion(msg.get("content", ""))
        if is_done and requirements:
            return requirements

    # Fallback: flatten full conversation
    return "\n".join(f"{msg['role']}: {msg['content']}" for msg in history)


async def run_bom_pricing_proposal(
    client: AzureAIAgentClient,
    requirements_text: str,
    bom_items: List[Dict[str, Any]] = None,
) -> ProposalBundle:
    """Execute Pricing → Proposal workflow using BOM from Architect Agent.
    
    Args:
        client: Azure AI Agent client
        requirements_text: Requirements text
        bom_items: BOM items already built by Architect Agent
    
    Returns:
        ProposalBundle with pricing and proposal
    """
    pricing_agent = create_pricing_agent(client)
    proposal_agent = create_proposal_agent(client)

    # BOM already built by Architect Agent - workflow is now: Pricing → Proposal
    workflow = SequentialBuilder().participants([pricing_agent, proposal_agent]).build()

    bom_text = json.dumps(bom_items or [], indent=2)
    pricing_output = ""
    proposal_output = ""
    current_agent = ""

    cm = _stage_span("Preparing pricing", requirements_length=len(requirements_text or ""))
    current_stage = "pricing"
    cm.__enter__()

    try:
        async for event in workflow.run_stream(requirements_text):
            if isinstance(event, ExecutorInvokedEvent) and getattr(event, "executor_id", None):
                current_agent = event.executor_id
                if current_agent == "proposal_agent" and current_stage != "proposal":
                    cm.__exit__(None, None, None)
                    cm = _stage_span(
                        "Preparing proposal", requirements_length=len(requirements_text or "")
                    )
                    cm.__enter__()
                    current_stage = "proposal"
                continue

            if isinstance(event, AgentRunUpdateEvent):
                text = event.data.text if getattr(event, "data", None) else None
                if not text:
                    continue

                if current_agent == "pricing_agent":
                    pricing_output += text
                elif current_agent == "proposal_agent":
                    proposal_output += text
    finally:
        cm.__exit__(None, None, None)

    # Parse and validate pricing output
    try:
        pricing_result = parse_pricing_response(pricing_output)

        # Validate total_monthly calculation
        calculated_total = sum(
            item["monthly_cost"] * item["quantity"] for item in pricing_result["items"]
        )

        if abs(calculated_total - pricing_result["total_monthly"]) > 0.01:
            logger.warning(
                f"Pricing total mismatch: calculated ${calculated_total:.2f} "
                f"vs reported ${pricing_result['total_monthly']:.2f}"
            )
            # Correct the total
            pricing_result["total_monthly"] = calculated_total

        logger.info(
            f"Pricing validated: {len(pricing_result['items'])} items, "
            f"total ${pricing_result['total_monthly']:.2f}"
        )
    except ValueError as e:
        logger.error(f"Pricing schema validation failed: {e}")
        raise

    return ProposalBundle(
        bom_text=bom_text,
        pricing_text=pricing_output,
        proposal_text=proposal_output,
    )


async def run_bom_pricing_proposal_stream(
    client: AzureAIAgentClient,
    requirements_text: str,
    bom_items: List[Dict[str, Any]] = None,
):
    """
    Execute Pricing → Proposal workflow with streaming progress events.

    Args:
        client: Azure AI Agent client
        requirements_text: User requirements summary
        bom_items: BOM items already built by Architect Agent

    Yields:
        ProgressEvent: Progress updates throughout the workflow
    """
    from src.core.models import ProgressEvent

    pricing_agent = create_pricing_agent(client)
    proposal_agent = create_proposal_agent(client)

    # BOM already built by Architect Agent - workflow is now: Pricing → Proposal
    workflow = SequentialBuilder().participants([pricing_agent, proposal_agent]).build()

    bom_text = json.dumps(bom_items or [], indent=2)
    pricing_output = ""
    proposal_output = ""
    current_agent = ""

    cm = _stage_span("Preparing pricing", requirements_length=len(requirements_text or ""))
    current_stage = "pricing"
    cm.__enter__()

    try:
        async for event in workflow.run_stream(requirements_text):
            # Track which agent is running
            if isinstance(event, ExecutorInvokedEvent) and getattr(event, "executor_id", None):
                current_agent = event.executor_id
                if current_agent == "proposal_agent" and current_stage != "proposal":
                    cm.__exit__(None, None, None)
                    cm = _stage_span(
                        "Preparing proposal", requirements_length=len(requirements_text or "")
                    )
                    cm.__enter__()
                    current_stage = "proposal"

                # Yield agent start event
                yield ProgressEvent(
                    event_type="agent_start",
                    agent_name=current_agent,
                    message=f"Starting {current_agent.replace('_', ' ').title()}...",
                )
                continue

            # Stream agent text updates
            if isinstance(event, AgentRunUpdateEvent):
                text = event.data.text if getattr(event, "data", None) else None
                if not text:
                    continue

                # Accumulate output for each agent
                if current_agent == "pricing_agent":
                    pricing_output += text
                elif current_agent == "proposal_agent":
                    proposal_output += text

                # Yield progress event with text chunk
                yield ProgressEvent(
                    event_type="agent_progress", agent_name=current_agent, message=text
                )

        # Validate pricing output
        pricing_result = parse_pricing_response(pricing_output)
        if pricing_result and pricing_result.get("items"):
            # Recalculate total for validation
            calculated_total = sum(
                item.get("monthly_cost", 0) * item.get("quantity", 1)
                for item in pricing_result.get("items", [])
            )
            reported_total = pricing_result.get("total_monthly", 0)

            if abs(calculated_total - reported_total) > 0.01:
                logger.warning(
                    f"Pricing total mismatch: calculated ${calculated_total:.2f} "
                    f"vs reported ${reported_total:.2f}"
                )
                # Update pricing output with corrected total
                pricing_result["total_monthly"] = calculated_total
                pricing_output = json.dumps(pricing_result, indent=2)

        # Yield workflow completion with all outputs
        yield ProgressEvent(
            event_type="workflow_complete",
            agent_name="",
            message="Workflow complete",
        )

    except Exception as e:
        logger.error(f"Error in streaming workflow: {e}")
        yield ProgressEvent(
            event_type="error",
            agent_name=current_agent or "unknown",
            message=f"Error: {str(e)}",
            data={"error": str(e)},
        )
    finally:
        cm.__exit__(None, None, None)


async def reset_session(session_store: InMemorySessionStore, session_id: str) -> None:
    """Clear session state."""
    session_store.delete(session_id)


def parse_question_completion(response_text: str) -> Tuple[bool, Optional[str]]:
    """Parse Question Agent response for completion flag and requirements summary.

    Supports structured JSON payloads. Prefers ```json code blocks and logs warnings
    if JSON is found in non-standard formats.
    """

    if not response_text:
        return False, None

    # Try code block extraction first (preferred format)
    obj = _extract_json_from_code_block(response_text)
    extraction_method = "code_block"

    # Fall back to other formats if code block not found
    if obj is None:
        obj = _extract_json_object(response_text)
        extraction_method = "other_format"

        if obj is not None:
            logger.warning(
                "Question Agent returned JSON but not in ```json code block format. "
                "Please update agent instructions to use proper format."
            )

    if isinstance(obj, dict):
        done = bool(obj.get("done"))
        requirements = (
            obj.get("requirements") or obj.get("requirements_summary") or obj.get("summary")
        )

        if done and requirements:
            logger.info(
                f"Completion detected (extraction method: {extraction_method}), "
                f"requirements: {requirements[:80]}..."
            )

        return done, requirements

    return False, None


def _extract_json_from_code_block(text: str) -> Optional[Any]:
    """Extract JSON from ```json code block specifically.

    Returns None if no code block found, so fallback logic can try other formats.
    """
    # Try ```json code block first (preferred format)
    pattern = r"```json\s*(\{.*?\})\s*```"
    match = re.search(pattern, text, flags=re.DOTALL)

    if match:
        candidate = match.group(1)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON from code block: {candidate}")
            return None

    return None


def _extract_json_object(text: str) -> Optional[Any]:
    """Extract a JSON object from plain text or fenced code blocks."""

    patterns = [
        r"```json\s*(\{.*?\})\s*```",
        r"```\s*(\{.*?\})\s*```",
        r"(\{.*\})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.DOTALL)
        if not match:
            continue
        candidate = match.group(1)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    try:
        return json.loads(text.strip())
    except Exception:
        return None
