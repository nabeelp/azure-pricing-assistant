"""Playwright MCP tool wrapper supporting both STDIO and HTTP transports."""

import logging
from typing import Optional

from agent_framework import MCPStreamableHTTPTool
from agent_framework_azure_ai import AzureAIAgentClient

from src.core.config import get_playwright_mcp_transport, get_playwright_mcp_url

logger = logging.getLogger(__name__)


def create_playwright_mcp_tool(
    client: Optional[AzureAIAgentClient] = None,
    transport: Optional[str] = None,
    url: Optional[str] = None,
) -> MCPStreamableHTTPTool:
    """
    Create a Playwright MCP tool with the appropriate transport.
    
    Args:
        client: Optional Azure AI Agent client (required for HTTP transport)
        transport: Optional transport override ('stdio' or 'http'). 
                   If not provided, uses PLAYWRIGHT_MCP_TRANSPORT env var.
        url: Optional URL override for HTTP transport.
             If not provided, uses PLAYWRIGHT_MCP_URL env var.
    
    Returns:
        Configured Playwright MCP tool
        
    Raises:
        ValueError: If transport is invalid or required parameters are missing
    """
    # Determine transport type
    transport_type = transport if transport else get_playwright_mcp_transport()
    
    if transport_type not in ["stdio", "http"]:
        raise ValueError(
            f"Invalid transport type '{transport_type}'. Must be 'stdio' or 'http'."
        )
    
    logger.info(f"Creating Playwright MCP tool with {transport_type.upper()} transport")
    
    if transport_type == "stdio":
        # STDIO transport for local development
        # Note: MCPStreamableHTTPTool doesn't directly support STDIO in the current implementation.
        # This is a placeholder for when STDIO support is added to the agent framework.
        # For now, we'll use HTTP transport with a local endpoint.
        logger.warning(
            "STDIO transport requested but not yet supported. "
            "Falling back to HTTP transport at default endpoint."
        )
        endpoint = url if url else get_playwright_mcp_url()
        
        return MCPStreamableHTTPTool(
            name="Playwright Browser Automation",
            description=(
                "Browser automation tool using Playwright. Provides capabilities to "
                "navigate web pages, interact with elements, fill forms, and extract data "
                "from web applications like the Azure Pricing Calculator."
            ),
            url=endpoint,
            chat_client=client,
        )
    
    else:  # http transport
        if not client:
            raise ValueError("HTTP transport requires an Azure AI Agent client")
        
        endpoint = url if url else get_playwright_mcp_url()
        
        return MCPStreamableHTTPTool(
            name="Playwright Browser Automation",
            description=(
                "Browser automation tool using Playwright. Provides capabilities to "
                "navigate web pages, interact with elements, fill forms, and extract data "
                "from web applications like the Azure Pricing Calculator."
            ),
            url=endpoint,
            chat_client=client,
        )


def get_playwright_tool_description() -> str:
    """
    Return a detailed description of Playwright MCP capabilities.
    
    This can be used in agent instructions to help them understand
    what the tool can do.
    """
    return """
Playwright MCP provides browser automation capabilities through the following tools:

**Navigation:**
- browser_navigate: Navigate to a URL
- browser_navigate_back: Go back to previous page

**Interaction:**
- browser_click: Click on an element
- browser_type: Type text into an input field
- browser_fill_form: Fill multiple form fields at once
- browser_select_option: Select option from dropdown
- browser_hover: Hover over an element
- browser_drag: Drag and drop between elements

**Information Gathering:**
- browser_snapshot: Get accessibility tree snapshot of the page (structured data)
- browser_take_screenshot: Take a visual screenshot
- browser_console_messages: Get console log messages
- browser_network_requests: Get network request information

**Evaluation:**
- browser_evaluate: Execute JavaScript in the browser context

**Session Management:**
- browser_tabs: List, create, close, or select browser tabs
- browser_wait_for: Wait for text to appear/disappear or time to pass

All interactions use the accessibility tree for reliability, making them robust
to UI changes and suitable for AI-driven automation.
"""
