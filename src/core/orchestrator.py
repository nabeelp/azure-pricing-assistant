"""Shared orchestration helpers for CLI and web interfaces."""

import json
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
from .models import ProposalBundle, SessionData
from .session import InMemorySessionStore


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

    response_text = ""
    async for update in question_agent.run_stream(user_message, thread=thread):
        if update.text:
            response_text += update.text

    session_data.history.append({"role": "user", "content": user_message})
    session_data.history.append({"role": "assistant", "content": response_text})
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

    return ProposalBundle(
        bom_text=bom_output,
        pricing_text=pricing_output,
        proposal_text=proposal_output,
    )


def reset_session(session_store: InMemorySessionStore, session_id: str) -> None:
    """Clear session state."""
    session_store.delete(session_id)


def parse_question_completion(response_text: str) -> Tuple[bool, Optional[str]]:
    """Parse Question Agent response for completion flag and requirements summary.

    Supports structured JSON payloads.
    """

    if not response_text:
        return False, None

    obj = _extract_json_object(response_text)

    if isinstance(obj, dict):
        done = bool(obj.get("done"))
        requirements = (
            obj.get("requirements")
            or obj.get("requirements_summary")
            or obj.get("summary")
        )
        return done, requirements


    return False, None


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
