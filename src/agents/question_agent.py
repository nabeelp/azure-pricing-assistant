"""Question Agent - Gathers Azure requirements through interactive Q&A."""

from agent_framework import ChatAgent
from agent_framework_azure_ai import AzureAIAgentClient


def create_question_agent(client: AzureAIAgentClient) -> ChatAgent:
    """
    Create Question Agent with Phase 1 mock instructions.
    
    This agent asks 1-2 simple questions and terminates with "We are DONE!"
    """
    instructions = """You are an Azure solutions specialist helping customers price their Azure infrastructure.

Your role is to gather basic requirements through a brief conversation. Ask ONE question at a time.

Ask about:
1. What type of workload (web app, database, etc.)
2. What Azure region they prefer

After getting answers to these questions, provide a brief summary of their requirements and end your response with exactly "We are DONE!"

Keep questions simple and conversational."""

    agent = ChatAgent(
        chat_client=client,
        instructions=instructions,
        name="question_agent"
    )
    
    return agent
