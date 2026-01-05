"""Shared orchestration helpers for CLI and web interfaces."""

from typing import Any, Dict, List, Tuple

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

    is_done = "We are DONE!" in response_text

    return {
        "response": response_text,
        "is_done": is_done,
        "history": session_data.history,
    }


def history_to_requirements(history: List[Dict[str, str]]) -> str:
    """Flatten chat history into a single requirements string."""
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
