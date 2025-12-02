"""Azure Seller Assistant - Multi-agent workflow for Azure pricing and proposals."""

import asyncio
import os
import sys
import warnings
from dotenv import load_dotenv
from azure.identity.aio import DefaultAzureCredential
from agent_framework_azure_ai import AzureAIAgentClient
from agent_framework import ExecutorInvokedEvent, SequentialBuilder
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


def suppress_async_generator_errors(loop, context):
    """Custom exception handler to suppress async generator cleanup errors during shutdown."""
    message = context.get("message", "")
    exception = context.get("exception")
    
    # Suppress known MCP client cleanup errors during shutdown
    if "streamablehttp_client" in message or (
        exception and "cancel scope" in str(exception)
    ):
        return  # Suppress these errors
    
    # For other errors, use default handling
    loop.default_exception_handler(context)


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
    
    # Fully consume the stream to avoid context detachment issues
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
        
        # Fully consume the stream to avoid context detachment issues
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
    
    current_agent_name = ""
    proposal_output = ""
    all_output = ""
    
    # Fully consume the stream to avoid context detachment issues
    async for event in workflow.run_stream(requirements):
        if isinstance(event, ExecutorInvokedEvent):
            # Track when a new agent starts
            if hasattr(event, 'executor_id') and event.executor_id:
                agent_name = event.executor_id
                if agent_name != current_agent_name:
                    current_agent_name = agent_name
                    print(f"\n--- {current_agent_name} ---\n")
        
        elif isinstance(event, AgentRunUpdateEvent):
            # Collect agent output
            if event.data and event.data.text:
                # Show agent output in real-time (streaming)
                event_output = event.data.text
                all_output += event_output

                # Capture proposal agent output specifically
                if current_agent_name == "proposal_agent":
                    proposal_output += event_output
    
    print("\n\n" + "=" * 60)
    print("=== Final Proposal ===")
    print("=" * 60 + "\n")
    print(proposal_output)
    
    return proposal_output


async def main():
    """Main entry point for Azure Seller Assistant."""
    # Load environment variables
    load_dotenv()

    # Setup observability
    setup_observability()
    
    endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    if not endpoint:
        print("Error: AZURE_AI_PROJECT_ENDPOINT not set in .env file")
        print("Please copy .env.example to .env and configure your Azure AI Foundry endpoint")
        return
    
    print("Azure Seller Assistant")
    print("=" * 60)
    
    # Create Azure AI client
    async with DefaultAzureCredential() as credential:
        async with AzureAIAgentClient(
            project_endpoint=endpoint,
            async_credential=credential
        ) as client:
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
    # Set up event loop with custom exception handler to suppress MCP cleanup errors
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.set_exception_handler(suppress_async_generator_errors)
    
    try:
        loop.run_until_complete(main())
    finally:
        # Clean shutdown
        try:
            # Cancel all pending tasks
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            
            # Wait for cancellation with a timeout
            if pending:
                loop.run_until_complete(asyncio.wait(pending, timeout=2.0))
            
            # Shutdown async generators
            loop.run_until_complete(loop.shutdown_asyncgens())
        except Exception:
            pass  # Suppress shutdown errors
        finally:
            loop.close()
