"""BOM Agent - Generates Bill of Materials (Phase 1: Mock)."""

from agent_framework import ChatAgent
from agent_framework_azure_ai import AzureAIAgentClient


def create_bom_agent(client: AzureAIAgentClient) -> ChatAgent:
    """
    Create BOM Agent with Phase 1 mock instructions.
    
    Returns hardcoded JSON array for testing workflow.
    """
    instructions = """You are an Azure infrastructure specialist.

Return this exact JSON array:
[
  {
    "serviceName": "Virtual Machines",
    "sku": "Standard_D2s_v3",
    "quantity": 2,
    "region": "East US",
    "armRegionName": "eastus",
    "hours_per_month": 730
  }
]

Return ONLY the JSON, no additional text."""

    agent = ChatAgent(
        chat_client=client,
        instructions=instructions,
        name="bom_agent"
    )
    
    return agent
