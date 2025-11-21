"""Azure Seller Assistant - Phase 1 Implementation."""

import asyncio
import os
from dotenv import load_dotenv
from azure.identity.aio import DefaultAzureCredential
from agent_framework_azure_ai import AzureAIAgentClient
from agent_framework import SequentialBuilder
from agent_framework import WorkflowOutputEvent, AgentRunUpdateEvent
from agent_framework.observability import setup_observability, get_tracer
from opentelemetry.trace import SpanKind

from src.agents import (
    create_question_agent,
    create_bom_agent,
    create_pricing_agent,
    create_proposal_agent,
)
from src.agents.bom_agent import parse_bom_response


async def run_question_workflow(client: AzureAIAgentClient):
    """
    Run interactive chat with Question Agent to gather requirements.
    
    Uses ChatAgent.run_stream() with thread-based conversation management.
    Returns requirements summary when "We are DONE!" is detected.
    """
    print("\n=== Starting Requirements Gathering ===\n")
    
    # Create Question Agent
    question_agent = create_question_agent(client)
    
    # Create a thread for multi-turn conversation
    thread = question_agent.get_new_thread()
    
    # Initial greeting from agent
    initial_message = "Hello! I'll help you price an Azure solution. Let's start!"
    print("Agent: ", end='', flush=True)
    
    last_response = ""
    
    async for update in question_agent.run_stream(initial_message, thread=thread):
        if update.text:
            print(update.text, end='', flush=True)
            last_response += update.text
    
    print("\n")
    
    # Interactive loop for conversation (max 20 turns)
    max_turns = 20
    requirements_summary = ""
    
    for turn in range(max_turns):
        # Get user input
        user_input = input("You: ")
        if not user_input.strip():
            continue
        
        # Stream agent response
        print("Agent: ", end='', flush=True)
        last_response = ""
        
        async for update in question_agent.run_stream(user_input, thread=thread):
            if update.text:
                print(update.text, end='', flush=True)
                last_response += update.text
        
        print("\n")
        
        # Check if agent is done
        if "We are DONE!" in last_response:
            requirements_summary = last_response
            print("✅ Requirements gathering complete!\n")
            break
    else:
        # Max turns reached without completion
        raise RuntimeError(f"Conversation exceeded {max_turns} turns without completion")
    
    if not requirements_summary:
        raise RuntimeError("Agent did not provide requirements summary")
    
    return requirements_summary


async def run_sequential_workflow(client: AzureAIAgentClient, requirements: str):
    """
    Run sequential workflow: BOM → Pricing → Proposal.
    
    Returns final proposal document.
    """
    print("\n=== Starting BOM → Pricing → Proposal Workflow ===\n")
    
    # Create agents
    bom_agent = create_bom_agent(client)
    pricing_agent = create_pricing_agent(client)
    proposal_agent = create_proposal_agent(client)
    
    # Build sequential workflow
    workflow = SequentialBuilder().participants([
        bom_agent,
        pricing_agent,
        proposal_agent
    ]).build()
    
    # Run workflow
    print("Processing requirements through agents...\n")
    
    final_proposal = ""
    bom_response = ""
    current_agent_output = ""
    
    async for event in workflow.run_stream(requirements):
        if isinstance(event, AgentRunUpdateEvent):
            # Collect agent output
            if event.data and event.data.text:
                current_agent_output += event.data.text
                # Show agent output in real-time
                print(event.data.text, end='', flush=True)
        
        elif isinstance(event, WorkflowOutputEvent):
            # Parse and validate BOM JSON if this is BOM agent output
            if not bom_response:
                try:
                    print("\n\n=== Parsing BOM JSON ===")
                    bom_data = parse_bom_response(current_agent_output)
                    print(f"✅ Validated BOM with {len(bom_data)} items:")
                    for item in bom_data:
                        print(f"  - {item['serviceName']} ({item['sku']}) x{item['quantity']} in {item['region']}")
                    bom_response = current_agent_output
                    current_agent_output = ""
                except ValueError as e:
                    print(f"\n❌ BOM Validation Error: {e}")
                    raise
            
            # Extract final proposal
            for msg in event.data:
                if msg.role.value == "assistant":
                    final_proposal += msg.text + "\n\n"
            
            print("\n=== Final Proposal ===\n")
            print(final_proposal)
            break
    
    return final_proposal


async def main():
    """Main entry point for Phase 1 implementation."""
    # Load environment variables
    load_dotenv()

    # Setup observability
    setup_observability()
    
    endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    if not endpoint:
        print("Error: AZURE_AI_PROJECT_ENDPOINT not set in .env file")
        print("Please copy .env.example to .env and configure your Azure AI Foundry endpoint")
        return
    
    print("Azure Seller Assistant - Phase 1 (Mock Implementation)")
    print("=" * 60)
    
    # Create Azure AI client
    async with DefaultAzureCredential() as credential:
        client = AzureAIAgentClient(
            project_endpoint=endpoint,
            async_credential=credential
        )
        
        try:
            with get_tracer().start_as_current_span("Azure Seller Assistant", kind=SpanKind.CLIENT) as top_span:
                    
                # Step 1: Requirements gathering via handoff workflow
                with get_tracer().start_as_current_span("Requirements Gathering", kind=SpanKind.CLIENT) as requirements_span:
                    requirements = await run_question_workflow(client)
                
                if not requirements:
                    print("Error: No requirements gathered")
                    return
                
                # Step 2: BOM → Pricing → Proposal via sequential workflow
                with get_tracer().start_as_current_span("Proposal Workflow", kind=SpanKind.CLIENT) as proposal_span:
                    proposal = await run_sequential_workflow(client, requirements)
                
                print("\n" + "=" * 60)
                print("Workflow completed successfully!")
                
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
