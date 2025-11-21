"""Pricing Agent - Calculates costs (Phase 1: Mock)."""

from agent_framework import ChatAgent
from agent_framework_azure_ai import AzureAIAgentClient


def create_pricing_agent(client: AzureAIAgentClient) -> ChatAgent:
    """
    Create Pricing Agent with Phase 1 mock instructions.
    
    Returns hardcoded pricing data for testing workflow.
    """
    instructions = """You are an Azure pricing specialist.

Return this exact JSON:
{
  "items": [
    {
      "service": "Virtual Machines",
      "sku": "Standard_D2s_v3",
      "monthly_cost": 100.00
    }
  ],
  "total_monthly": 100.00
}

Return ONLY the JSON, no additional text."""

    agent = ChatAgent(
        chat_client=client,
        instructions=instructions,
        name="pricing_agent"
    )
    
    return agent
