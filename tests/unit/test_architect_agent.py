"""Unit tests for Architect Agent - Azure Solutions Architect."""

import pytest
from unittest.mock import MagicMock
from agent_framework import ChatAgent
from agent_framework_azure_ai import AzureAIAgentClient

from src.agents.architect_agent import create_architect_agent, extract_partial_bom_from_response
from src.core.orchestrator import parse_question_completion


class TestArchitectAgentCreation:
    """Test Architect Agent initialization and configuration."""

    def test_create_architect_agent_with_mock_client(self):
        """Should create Architect Agent with mocked Azure AI client."""
        mock_client = MagicMock(spec=AzureAIAgentClient)
        
        agent = create_architect_agent(mock_client)
        
        assert agent is not None
        assert isinstance(agent, ChatAgent)
        assert agent.name == "architect_agent"

    def test_agent_has_microsoft_docs_tool(self):
        """Should configure Microsoft Learn MCP tool."""
        mock_client = MagicMock(spec=AzureAIAgentClient)
        
        agent = create_architect_agent(mock_client)
        
        # Verify agent was created with Microsoft Learn tool
        import inspect
        source = inspect.getsource(create_architect_agent)
        assert "Microsoft Learn" in source
        assert "learn.microsoft.com" in source


class TestPartialBOMExtraction:
    """Test partial BOM extraction from architect responses."""

    def test_extract_partial_bom_from_identified_services(self):
        """Should extract BOM items from identified_services JSON."""
        response = '''Let me check what Azure services would work well...

{
  "identified_services": [
    {
      "serviceName": "App Service",
      "sku": "P1v3",
      "quantity": 2,
      "region": "East US",
      "armRegionName": "eastus",
      "hours_per_month": 730,
      "confidence": "high",
      "notes": "Premium tier for production"
    }
  ]
}

What do you think about this option?'''
        
        items = extract_partial_bom_from_response(response)
        
        assert len(items) == 1
        assert items[0]["serviceName"] == "App Service"
        assert items[0]["sku"] == "P1v3"
        assert items[0]["quantity"] == 2
        assert items[0]["region"] == "East US"

    def test_extract_partial_bom_from_completion_format(self):
        """Should extract BOM items from completion format with bom_items."""
        response = '''```json
{
  "requirements": "Workload: web app; Region: East US; Services: App Service P1v3",
  "done": true,
  "bom_items": [
    {
      "serviceName": "App Service",
      "sku": "P1v3",
      "quantity": 1,
      "region": "East US",
      "armRegionName": "eastus",
      "hours_per_month": 730
    }
  ]
}
```'''
        
        items = extract_partial_bom_from_response(response)
        
        assert len(items) == 1
        assert items[0]["serviceName"] == "App Service"
        assert items[0]["sku"] == "P1v3"

    def test_extract_partial_bom_returns_empty_when_none_found(self):
        """Should return empty list when no BOM items found."""
        response = "What scale are we talking about - how many users do you expect?"
        
        items = extract_partial_bom_from_response(response)
        
        assert items == []

    def test_extract_partial_bom_handles_multiple_items(self):
        """Should extract multiple BOM items."""
        response = '''{
  "identified_services": [
    {
      "serviceName": "App Service",
      "sku": "P1v3",
      "quantity": 2,
      "region": "East US",
      "armRegionName": "eastus",
      "hours_per_month": 730
    },
    {
      "serviceName": "SQL Database",
      "sku": "S1",
      "quantity": 1,
      "region": "East US",
      "armRegionName": "eastus",
      "hours_per_month": 730
    }
  ]
}'''
        
        items = extract_partial_bom_from_response(response)
        
        assert len(items) == 2
        assert items[0]["serviceName"] == "App Service"
        assert items[1]["serviceName"] == "SQL Database"


class TestArchitectInstructions:
    """Test architect agent instructions and capabilities."""

    def test_instructions_mention_azure_solutions_architect(self):
        """Should identify as Azure Solutions Architect."""
        mock_client = MagicMock(spec=AzureAIAgentClient)
        agent = create_architect_agent(mock_client)
        
        import inspect
        source = inspect.getsource(create_architect_agent)
        
        assert "Azure Solutions Architect" in source

    def test_instructions_include_tool_descriptions(self):
        """Should include descriptions for all tools."""
        mock_client = MagicMock(spec=AzureAIAgentClient)
        agent = create_architect_agent(mock_client)
        
        import inspect
        source = inspect.getsource(create_architect_agent)
        
        # Check for tool descriptions
        assert "microsoft_docs_search" in source
    def test_instructions_include_progressive_bom_building(self):
        """Should include instructions for progressive BOM building."""
        mock_client = MagicMock(spec=AzureAIAgentClient)
        agent = create_architect_agent(mock_client)
        
        import inspect
        source = inspect.getsource(create_architect_agent)
        
        assert "PROGRESSIVE SERVICE IDENTIFICATION" in source or "progressive" in source.lower()
        assert "identified_services" in source
        assert "confidence" in source

    def test_instructions_include_architecture_components(self):
        """Should ask about architectural components."""
        mock_client = MagicMock(spec=AzureAIAgentClient)
        agent = create_architect_agent(mock_client)
        
        import inspect
        source = inspect.getsource(create_architect_agent)
        
        # Check for architecture-related keywords
        assert "private networking" in source.lower() or "VNet" in source
        assert "Application Gateway" in source or "Load Balancer" in source
        assert "WAF" in source or "Web Application Firewall" in source

    def test_instructions_include_service_catalog(self):
        """Should use static service catalog for recommendations."""
        mock_client = MagicMock(spec=AzureAIAgentClient)
        agent = create_architect_agent(mock_client)
        
        import inspect
        source = inspect.getsource(create_architect_agent)
        
        # Check for service catalog usage
        assert "service catalog" in source.lower() or "list_all_services" in source


class TestCompletionFormat:
    """Test completion format with BOM items."""

    def test_completion_includes_bom_items(self):
        """Should include bom_items in completion format."""
        response = '''```json
{
  "requirements": "Workload: web app; Region: East US; Services: App Service P1v3",
  "done": true,
  "bom_items": [
    {
      "serviceName": "App Service",
      "sku": "P1v3",
      "quantity": 1,
      "region": "East US",
      "armRegionName": "eastus",
      "hours_per_month": 730
    }
  ]
}
```'''
        
        done, requirements = parse_question_completion(response)
        
        assert done is True
        assert "web app" in requirements
        assert "East US" in requirements

    def test_completion_format_documented_in_instructions(self):
        """Should document completion format with bom_items."""
        mock_client = MagicMock(spec=AzureAIAgentClient)
        agent = create_architect_agent(mock_client)
        
        import inspect
        source = inspect.getsource(create_architect_agent)
        
        assert "FINAL RESPONSE FORMAT" in source
        assert '"done": true' in source
        assert '"bom_items"' in source or 'bom_items' in source
