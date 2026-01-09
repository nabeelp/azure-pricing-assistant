"""Azure Pricing Assistant - CLI entry point."""

import asyncio
import logging
import os

from agent_framework.observability import get_tracer
from opentelemetry import trace
from opentelemetry.trace import SpanKind

from src.core.config import load_environment
from src.cli.interface import CLIInterface
from src.cli.prompts import (
    print_agent_response,
    print_completion_message,
    print_error,
    print_final_message,
    print_proposal_header,
    print_workflow_start,
    print_agent_start,
    print_agent_progress,
    print_agent_complete,
    print_requirements_summary,
)
from src.shared.async_utils import create_event_loop
from src.shared.errors import WorkflowError
from src.shared.logging import setup_logging
from src.shared.tracing import configure_tracing


async def run_cli_workflow() -> None:
    """Run the CLI workflow for Azure Pricing Assistant."""
    print_workflow_start()

    interface = CLIInterface()
    session_id = "cli-session"

    # Initial greeting
    greeting = "Hello! I'll help you price an Azure solution. Let's start!"
    first_turn = await interface.chat_turn(session_id, greeting)

    if "error" in first_turn:
        print_error(first_turn["error"])
        return

    print_agent_response(first_turn["response"])

    max_turns = 20
    requirements_summary = ""
    is_done = False

    # Interactive chat loop
    for turn_num in range(1, max_turns + 1):
        user_input = input("You: ")
        if not user_input.strip():
            continue

        turn_result = await interface.chat_turn(session_id, user_input)

        if "error" in turn_result:
            print_error(turn_result["error"])
            continue

        print_agent_response(turn_result["response"])

        if turn_result.get("is_done", False):
            is_done = True
            requirements_summary = turn_result.get("requirements_summary", turn_result["response"])
            
            # Show friendly summary instead of raw JSON
            print_requirements_summary(requirements_summary)
            
            # Ask if ready to proceed
            while True:
                proceed_input = input("\nReady to generate proposal? (yes/no): ").strip().lower()
                if proceed_input in ("yes", "y"):
                    break
                elif proceed_input in ("no", "n"):
                    print("\nPlease continue with additional requirements or clarifications.\n")
                    is_done = False
                    break
                else:
                    print("Please enter 'yes' or 'no'.")
            
            if is_done:
                break
    else:
        raise WorkflowError(
            "Conversation exceeded 20 turns without completion. "
            "Agent did not emit { \"done\": true } in final response."
        )

    if not is_done:
        raise WorkflowError(
            "Conversation completed without proper completion signal. "
            "Agent must return JSON with { \"done\": true }."
        )
    
    if not requirements_summary:
        raise WorkflowError("Agent did not provide requirements summary")

    # Generate proposal workflow with progress
    print_header("Generating Proposal")

    bom_text = ""
    pricing_text = ""
    proposal_text = ""
    current_agent = ""

    async for event in interface.generate_proposal_stream(session_id):
        if "error" in event:
            print_error(event["error"])
            return
        
        event_type = event.get("event_type")
        agent_name = event.get("agent_name")
        message = event.get("message")
        data = event.get("data")
        
        if event_type == "agent_start":
            if current_agent:
                print_agent_complete(current_agent)
            current_agent = agent_name
            print_agent_start(agent_name)
        
        elif event_type == "agent_progress":
            if message:
                print_agent_progress(message)
        
        elif event_type == "workflow_complete":
            if current_agent:
                print_agent_complete(current_agent)
            
            bom_text = data.get("bom", "")
            pricing_text = data.get("pricing", "")
            proposal_text = data.get("proposal", "")
        
        elif event_type == "error":
            print_error(message or "Unknown error")
            return

    # Display final proposal
    print_proposal_header()
    print(proposal_text)
    print_final_message()


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 60}")
    print(f"=== {title}")
    print(f"{'=' * 60}\n")


async def main() -> None:
    """Main entry point for CLI."""
    load_environment()

    # Resolve desired log level from environment (default INFO)
    level_name = os.getenv("APP_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    # Configure logging with selected level
    setup_logging(
        name="pricing_assistant_cli",
        level=level,
        service_name="azure-pricing-assistant-cli",
    )

    # Configure OpenTelemetry traces (OTLP/gRPC) and enable Agent Framework spans.
    configure_tracing(service_name="azure-pricing-assistant-cli")

    print("Azure Pricing Assistant")
    print("=" * 60)

    tracer = get_tracer(instrumenting_module_name="azure_pricing_assistant.session")

    try:
        # Single long-lived span so all CLI logs correlate.
        session_span = tracer.start_span(
            name="session.cli",
            kind=SpanKind.CLIENT,
            attributes={"session.id": "cli-session", "session.type": "cli"},
        )
        with trace.use_span(session_span, end_on_exit=False):
            await run_cli_workflow()
    except Exception as e:
        print_error(str(e))
        import traceback

        traceback.print_exc()
    finally:
        try:
            session_span.end()
        except Exception:
            pass


if __name__ == "__main__":
    # Set up event loop with custom exception handler to suppress MCP cleanup errors
    loop = create_event_loop()
    asyncio.set_event_loop(loop)

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
