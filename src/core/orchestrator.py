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
    create_bom_agent,
    create_pricing_agent,
    create_proposal_agent,
    create_question_agent,
)
from src.agents.pricing_agent import parse_pricing_response
from src.shared.errors import WorkflowError
from src.shared.metrics import increment_errors
from .models import ProposalBundle, SessionData, PricingResult
from .session import InMemorySessionStore

# Configure logging
logger = logging.getLogger(__name__)


def _stage_span(stage_name: str, *, session_id: Optional[str] = None, **attrs: Any):
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


async def _run_bom_task_background(
    client: AzureAIAgentClient,
    session_store: InMemorySessionStore,
    session_id: str,
    recent_context: str,
) -> None:
    """
    Background task wrapper for run_incremental_bom_update.
    
    Handles state transitions and error handling for async BOM updates.
    Updates session state with task status and results.
    
    Args:
        client: Azure AI Agent client
        session_store: Session store
        session_id: Session identifier
        recent_context: Recent conversation context
    """
    session_data = session_store.get(session_id)
    if not session_data:
        logger.warning(f"No session data found for {session_id} in background task")
        return
    
    # Transition to processing state
    session_data.bom_task_status = "processing"
    session_data.bom_task_error = None
    session_store.set(session_id, session_data)
    
    try:
        # Run BOM update with 30s timeout
        bom_result = await asyncio.wait_for(
            run_incremental_bom_update(client, session_store, session_id, recent_context),
            timeout=30.0
        )
        
        # Update session with results
        session_data = session_store.get(session_id)
        if session_data:
            session_data.bom_task_status = "complete"
            session_data.bom_last_update = datetime.now()
            session_store.set(session_id, session_data)
            
            logger.info(f"Background BOM task complete for session {session_id}")
    
    except asyncio.TimeoutError:
        logger.error(f"BOM task timeout for session {session_id}", exc_info=True)
        increment_errors("bom_timeout", session_id=session_id)
        session_data = session_store.get(session_id)
        if session_data:
            session_data.bom_task_status = "error"
            session_data.bom_task_error = "BOM generation timed out after 30 seconds"
            session_store.set(session_id, session_data)
    
    except asyncio.CancelledError:
        logger.info(f"BOM task cancelled for session {session_id}")
        session_data = session_store.get(session_id)
        if session_data:
            session_data.bom_task_status = "idle"
            session_store.set(session_id, session_data)
        raise
    
    except Exception as e:
        # Log full traceback for debugging
        error_traceback = traceback.format_exc()
        logger.error(
            f"BOM task error for session {session_id}: {e}\n{error_traceback}",
            exc_info=True,
            extra={"session_id": session_id, "error_type": type(e).__name__}
        )
        increment_errors("bom_task_failure", session_id=session_id)
        
        session_data = session_store.get(session_id)
        if session_data:
            session_data.bom_task_status = "error"
            # Sanitize error message for UI (no traceback)
            session_data.bom_task_error = f"BOM generation failed: {str(e)}"
            session_store.set(session_id, session_data)


async def run_question_turn(
    client: AzureAIAgentClient,
    session_store: InMemorySessionStore,
    session_id: str,
    user_message: str,
    enable_incremental_bom: bool = True,
) -> Dict[str, Any]:
    """Run a single question-agent turn and persist thread/history.

    Args:
        client: Azure AI Agent client
        session_store: Session store
        session_id: Session identifier
        user_message: User's message
        enable_incremental_bom: Whether to trigger incremental BOM updates (default: True)

    Returns:
        Dict with response, is_done, requirements_summary, history, and optional bom_items
    """
    with _stage_span(
        "Asking questions",
        session_id=session_id,
        message_length=len(user_message or ""),
    ):
        question_agent = create_question_agent(client)

        session_data = session_store.get(session_id)
        if not session_data:
            thread = question_agent.get_new_thread()
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
        async for update in question_agent.run_stream(user_message, thread=thread):
            if update.text:
                response_text += update.text

        session_data.history.append({"role": "user", "content": user_message})
        session_data.history.append({"role": "assistant", "content": response_text})

        # Increment turn counter after successful run
        session_data.turn_count += 1
        session_store.set(session_id, session_data)

        is_done, requirements_summary = parse_question_completion(response_text)

        result = {
            "response": response_text,
            "is_done": is_done,
            "requirements_summary": requirements_summary,
            "history": session_data.history,
        }

        # Trigger incremental BOM update if enabled and conditions are met
        if enable_incremental_bom and should_trigger_bom_update(
            response_text, session_data.turn_count, session_data.history
        ):
            logger.info(f"Triggering incremental BOM update for session {session_id}")

            # Build recent context from last few exchanges
            recent_history = (
                session_data.history[-6:] if len(session_data.history) > 6 else session_data.history
            )
            recent_context = "\n".join(f"{msg['role']}: {msg['content']}" for msg in recent_history)

            # Cancel any existing BOM task
            if session_data.bom_task_handle and not session_data.bom_task_handle.done():
                logger.info(f"Cancelling previous BOM task for session {session_id}")
                session_data.bom_task_handle.cancel()
                try:
                    await session_data.bom_task_handle
                except asyncio.CancelledError:
                    pass

            # Set status to queued
            session_data.bom_task_status = "queued"
            session_store.set(session_id, session_data)

            # Spawn background BOM task (don't await)
            task = asyncio.create_task(
                _run_bom_task_background(client, session_store, session_id, recent_context)
            )
            
            # Store task handle for cancellation
            session_data.bom_task_handle = task
            session_store.set(session_id, session_data)

            result["bom_items"] = session_data.bom_items or []
            result["bom_updated"] = False  # Will be updated asynchronously
            result["bom_task_status"] = "queued"
        else:
            # Return current BOM items without update
            result["bom_items"] = session_data.bom_items or []
            result["bom_updated"] = False
            result["bom_task_status"] = session_data.bom_task_status

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
) -> ProposalBundle:
    """Execute BOM → Pricing → Proposal workflow (CLI logic reused)."""
    bom_agent = create_bom_agent(client)
    pricing_agent = create_pricing_agent(client)
    proposal_agent = create_proposal_agent(client)

    workflow = SequentialBuilder().participants([bom_agent, pricing_agent, proposal_agent]).build()

    bom_output = ""
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

                if current_agent == "bom_agent":
                    bom_output += text
                elif current_agent == "pricing_agent":
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
        bom_text=bom_output,
        pricing_text=pricing_output,
        proposal_text=proposal_output,
    )


async def run_bom_pricing_proposal_stream(
    client: AzureAIAgentClient,
    requirements_text: str,
):
    """
    Execute BOM → Pricing → Proposal workflow with streaming progress events.

    Args:
        client: Azure AI Agent client
        requirements_text: User requirements summary

    Yields:
        ProgressEvent: Progress updates throughout the workflow
    """
    from src.core.models import ProgressEvent

    bom_agent = create_bom_agent(client)
    pricing_agent = create_pricing_agent(client)
    proposal_agent = create_proposal_agent(client)

    workflow = SequentialBuilder().participants([bom_agent, pricing_agent, proposal_agent]).build()

    bom_output = ""
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
                if current_agent == "bom_agent":
                    bom_output += text
                elif current_agent == "pricing_agent":
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
            data={"bom": bom_output, "pricing": pricing_output, "proposal": proposal_output},
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


async def run_incremental_bom_update(
    client: AzureAIAgentClient,
    session_store: InMemorySessionStore,
    session_id: str,
    recent_context: str,
) -> Dict[str, Any]:
    """
    Run BOM agent to build/update BOM items incrementally.

    Args:
        client: Azure AI Agent client
        session_store: Session store for persisting BOM items
        session_id: Current session ID
        recent_context: Recent conversation context to analyze

    Returns:
        Dict with new/updated BOM items
    """
    from src.agents.bom_agent import parse_bom_response

    session_data = session_store.get(session_id)
    if not session_data:
        logger.warning(f"No session data found for {session_id}")
        return {"bom_items": [], "error": "No session found"}

    # Create BOM agent
    bom_agent = create_bom_agent(client)
    thread = bom_agent.get_new_thread()

    # Build prompt for incremental BOM update
    existing_bom = session_data.bom_items or []
    prompt = f"""Based on the following conversation context, analyze and create BOM items for any Azure services discussed.

EXISTING BOM ITEMS:
{json.dumps(existing_bom, indent=2) if existing_bom else "None yet"}

RECENT CONVERSATION CONTEXT:
{recent_context}

INSTRUCTIONS:
- If this is a new service/component not in the existing BOM, create a new BOM item for it
- If this updates an existing service (e.g., changing SKU), create the updated BOM item
- Only create BOM items for services that have enough information (service type, region, scale)
- Return ONLY the new or updated BOM items as a JSON array
- If no new BOM items can be created yet, return an empty array: []

Remember the schema:
[
  {{
    "serviceName": "Service Name",
    "sku": "SKU",
    "quantity": 1,
    "region": "Region Name",
    "armRegionName": "regioncode",
    "hours_per_month": 730
  }}
]"""

    # Run BOM agent
    response_text = ""
    try:
        async for update in bom_agent.run_stream(prompt, thread=thread):
            if update.text:
                response_text += update.text

        logger.info(f"BOM agent response: {response_text[:200]}...")

        # Parse BOM response (allow empty arrays in incremental mode)
        new_bom_items = parse_bom_response(response_text, allow_empty=True)

        # Merge with existing BOM (update or append)
        merged_bom = _merge_bom_items(existing_bom, new_bom_items)

        # Update session
        session_data.bom_items = merged_bom
        session_store.set(session_id, session_data)

        logger.info(f"Updated BOM: {len(merged_bom)} total items")

        return {
            "bom_items": merged_bom,
            "new_items": new_bom_items,
        }

    except Exception as e:
        logger.error(f"Error in incremental BOM update: {e}")
        return {"bom_items": existing_bom, "error": str(e)}


def _merge_bom_items(
    existing: List[Dict[str, Any]], new: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Merge new BOM items with existing ones.

    If a new item matches an existing one (same serviceName and region),
    update the existing item. Otherwise, append the new item.

    Args:
        existing: Existing BOM items
        new: New BOM items to merge

    Returns:
        Merged list of BOM items
    """
    if not new:
        return existing

    # Create a copy of existing items
    merged = list(existing)

    for new_item in new:
        # Find matching item (same service and region)
        match_idx = None
        for idx, existing_item in enumerate(merged):
            if existing_item.get("serviceName") == new_item.get(
                "serviceName"
            ) and existing_item.get("region") == new_item.get("region"):
                match_idx = idx
                break

        if match_idx is not None:
            # Update existing item
            logger.info(
                f"Updating BOM item: {new_item.get('serviceName')} " f"in {new_item.get('region')}"
            )
            merged[match_idx] = new_item
        else:
            # Add new item
            logger.info(
                f"Adding BOM item: {new_item.get('serviceName')} " f"in {new_item.get('region')}"
            )
            merged.append(new_item)

    return merged


def should_trigger_bom_update(
    response_text: str, turn_count: int, conversation_history: List[Dict[str, str]] = None
) -> bool:
    """
    Determine if the question agent's response indicates enough info for BOM update.

    Triggers BOM update when:
    - User has provided service details (mentions specific Azure services in history)
    - User has specified region and scale
    - Every 3 turns to catch accumulated information
    - When conversation is marked as done

    Args:
        response_text: Question agent's response
        turn_count: Current turn count
        conversation_history: Full conversation history (optional)

    Returns:
        True if BOM should be updated
    """
    # Check if done
    is_done, _ = parse_question_completion(response_text)
    if is_done:
        return True

    # Check for service/configuration mentions in conversation history
    service_indicators = [
        "app service",
        "web app",
        "web",
        "sql",
        "database",
        "storage",
        "virtual machine",
        "vm",
        "kubernetes",
        "aks",
        "function",
        "cosmos",
        "redis",
        "service bus",
        "event hub",
        "machine learning",
        "synapse",
        "sku",
        "tier",
        "region",
        "scale",
    ]

    has_service_info = False

    # Check agent response
    text_lower = response_text.lower()
    has_service_info = any(indicator in text_lower for indicator in service_indicators)

    # Also check conversation history if provided
    if not has_service_info and conversation_history:
        # Check user messages for service mentions
        for msg in conversation_history:
            if msg.get("role") == "user":
                msg_lower = msg.get("content", "").lower()
                if any(indicator in msg_lower for indicator in service_indicators):
                    has_service_info = True
                    break

    # Trigger every 3 turns OR when we detect service configuration
    should_trigger = (turn_count > 0 and turn_count % 3 == 0) or has_service_info

    if should_trigger:
        logger.info(
            f"Triggering BOM update at turn {turn_count}, has_service_info={has_service_info}"
        )

    return should_trigger


async def reset_session(session_store: InMemorySessionStore, session_id: str) -> None:
    """Clear session state and cancel any in-progress BOM tasks."""
    session_data = session_store.get(session_id)
    
    # Cancel any in-progress BOM task
    if session_data and session_data.bom_task_handle and not session_data.bom_task_handle.done():
        logger.info(f"Cancelling BOM task during session reset for {session_id}")
        session_data.bom_task_handle.cancel()
        try:
            await session_data.bom_task_handle
        except asyncio.CancelledError:
            pass
    
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
