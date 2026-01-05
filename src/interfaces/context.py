"""Execution context for interface operations."""

from typing import Optional

from azure.identity.aio import DefaultAzureCredential
from agent_framework_azure_ai import AzureAIAgentClient

from src.core.config import get_ai_endpoint
from src.core.session import InMemorySessionStore


class InterfaceContext:
    """
    Encapsulates Azure AI client and session management for interface operations.
    
    Can be used as an async context manager to ensure proper resource cleanup.
    """

    def __init__(self, session_store: Optional[InMemorySessionStore] = None):
        """
        Initialize the context.

        Args:
            session_store: Optional session store. If not provided, InMemorySessionStore is created.
        """
        self.client: Optional[AzureAIAgentClient] = None
        self.session_store = session_store or InMemorySessionStore()
        self._credential: Optional[DefaultAzureCredential] = None

    async def __aenter__(self) -> "InterfaceContext":
        """
        Set up Azure AI client for use within the context.

        Returns:
            The InterfaceContext instance.

        Raises:
            RuntimeError: If AZURE_AI_PROJECT_ENDPOINT is not configured.
        """
        try:
            endpoint = get_ai_endpoint()
        except RuntimeError as err:
            raise RuntimeError(f"Failed to initialize InterfaceContext: {err}") from err

        self._credential = DefaultAzureCredential()
        self.client = AzureAIAgentClient(
            project_endpoint=endpoint, credential=self._credential
        )
        # Note: client.__aenter__ is called when used with AzureAIAgentClient directly
        await self.client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Clean up Azure AI client and credential.

        Args:
            exc_type: Exception type if an error occurred
            exc_val: Exception value if an error occurred
            exc_tb: Exception traceback if an error occurred
        """
        if self.client:
            try:
                await self.client.__aexit__(exc_type, exc_val, exc_tb)
            except Exception:
                pass  # Suppress cleanup errors

        if self._credential:
            await self._credential.close()

    def validate(self) -> bool:
        """Check if context is properly initialized."""
        return self.client is not None and self.session_store is not None
