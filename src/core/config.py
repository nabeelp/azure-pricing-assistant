"""Shared configuration helpers for Azure Pricing Assistant."""

import os
from dotenv import load_dotenv

DEFAULT_PRICING_MCP_URL = "http://localhost:8080/mcp"


def load_environment() -> None:
    """Load environment variables from .env if present."""
    load_dotenv()


def get_ai_endpoint() -> str:
    """Return the Azure AI project endpoint or raise if missing."""
    endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    if not endpoint:
        raise RuntimeError(
            "AZURE_AI_PROJECT_ENDPOINT is not set. Configure your Azure AI Foundry endpoint."
        )
    return endpoint


def get_pricing_mcp_url() -> str:
    """Return the pricing MCP endpoint with a sensible default."""
    return os.getenv("AZURE_PRICING_MCP_URL", DEFAULT_PRICING_MCP_URL)


def get_flask_secret() -> str:
    """Return the Flask secret key or raise if missing."""
    secret = os.getenv("FLASK_SECRET_KEY")
    if not secret:
        raise RuntimeError(
            "FLASK_SECRET_KEY environment variable is not set. Set a strong value for production."
        )
    return secret


def get_port(default: int = 8000) -> int:
    """Return the desired port for local hosting."""
    try:
        return int(os.getenv("PORT", default))
    except ValueError:
        return default
