"""Shared orchestration helpers for CLI and web interfaces."""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from agent_framework import AgentRunUpdateEvent, ExecutorInvokedEvent, SequentialBuilder
from agent_framework_azure_ai import AzureAIAgentClient

from src.agents import (
    create_bom_agent,
    create_pricing_agent,
    create_proposal_agent,
    create_question_agent,
)
from src.agents.pricing_agent import parse_pricing_response
from src.shared.errors import WorkflowError
from .models import ProposalBundle, SessionData, PricingResult
from .session import InMemorySessionStore

# Configure logging
logger = logging.getLogger(__name__)


async def run_question_turn(
    client: AzureAIAgentClient,
    session_store: InMemorySessionStore,
    session_id: str,
    user_message: str,
) -> Dict[str, Any]:
    """Run a single question-agent turn and persist thread/history."""
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

    return {
        "response": response_text,
        "is_done": is_done,
        "requirements_summary": requirements_summary,
        "history": session_data.history,
    }


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

    workflow = SequentialBuilder().participants(
        [bom_agent, pricing_agent, proposal_agent]
    ).build()

    bom_output = ""
    pricing_output = ""
    proposal_output = ""
    current_agent = ""

    async for event in workflow.run_stream(requirements_text):
        if isinstance(event, ExecutorInvokedEvent) and getattr(event, "executor_id", None):
            current_agent = event.executor_id
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

    # Parse and validate pricing output
    try:
        pricing_result = parse_pricing_response(pricing_output)
        
        # Validate total_monthly calculation
        calculated_total = sum(
            item["monthly_cost"] * item["quantity"]
            for item in pricing_result["items"]
        )
        
        if abs(calculated_total - pricing_result["total_monthly"]) > 0.01:
            logger.warning(
                f"Pricing total mismatch: calculated ${calculated_total:.2f} "
                f"vs reported ${pricing_result['total_monthly']:.2f}"
            )
            # Correct the total
            pricing_result["total_monthly"] = calculated_total
        
        logger.info(f"Pricing validated: {len(pricing_result['items'])} items, "
                   f"total ${pricing_result['total_monthly']:.2f}")
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

    workflow = SequentialBuilder().participants(
        [bom_agent, pricing_agent, proposal_agent]
    ).build()

    bom_output = ""
    pricing_output = ""
    proposal_output = ""
    current_agent = ""

    try:
        async for event in workflow.run_stream(requirements_text):
            # Track which agent is running
            if isinstance(event, ExecutorInvokedEvent) and getattr(event, "executor_id", None):
                current_agent = event.executor_id
                # Yield agent start event
                yield ProgressEvent(
                    event_type="agent_start",
                    agent_name=current_agent,
                    message=f"Starting {current_agent.replace('_', ' ').title()}..."
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
                    event_type="agent_progress",
                    agent_name=current_agent,
                    message=text
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
            data={
                "bom": bom_output,
                "pricing": pricing_output,
                "proposal": proposal_output
            }
        )

    except Exception as e:
        logger.error(f"Error in streaming workflow: {e}")
        yield ProgressEvent(
            event_type="error",
            agent_name=current_agent or "unknown",
            message=f"Error: {str(e)}",
            data={"error": str(e)}
        )


def reset_session(session_store: InMemorySessionStore, session_id: str) -> None:
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
            obj.get("requirements")
            or obj.get("requirements_summary")
            or obj.get("summary")
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
