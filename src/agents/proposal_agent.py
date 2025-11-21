"""Proposal Agent - Generates customer proposals (Phase 1: Mock)."""

from agent_framework import ChatAgent
from agent_framework_azure_ai import AzureAIAgentClient


def create_proposal_agent(client: AzureAIAgentClient) -> ChatAgent:
    """
    Create Proposal Agent with Phase 1 mock instructions.
    
    Creates simple text-based proposal from conversation history.
    """
    instructions = """You are an Azure solutions consultant creating customer proposals.

Based on the conversation, create a brief proposal.

Format:
Azure Solution Proposal

Executive Summary:
[Brief description of solution]

Cost Breakdown:
[List services and costs]

Total Monthly Cost: $[amount]
Total Annual Cost: $[amount × 12]"""

    agent = ChatAgent(
        chat_client=client,
        instructions=instructions,
        name="proposal_agent"
    )
    
    return agent
