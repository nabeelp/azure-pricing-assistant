"""CLI prompts and formatting utilities."""


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 60}")
    print(f"=== {title}")
    print(f"{'=' * 60}\n")


def print_agent_response(response: str) -> None:
    """Print agent response with formatting."""
    print("Agent: ", end="", flush=True)
    print(response, flush=True)
    print()


def print_proposal_header() -> None:
    """Print the proposal section header."""
    print_header("Final Proposal")


def print_completion_message() -> None:
    """Print workflow completion message."""
    print("✅ Requirements gathering complete!\n")


def print_error(error: str) -> None:
    """Print error message."""
    print(f"❌ Error: {error}\n", flush=True)


def print_workflow_start() -> None:
    """Print workflow start message."""
    print_header("Starting Requirements Gathering")


def print_final_message() -> None:
    """Print final success message."""
    print("=" * 60)
    print("Workflow completed successfully!")
    print("=" * 60)
