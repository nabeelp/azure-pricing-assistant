"""Tests for Pricing Agent with Azure Pricing MCP integration."""

import unittest
from unittest.mock import MagicMock
from src.agents.pricing_agent import create_pricing_agent


class TestPricingAgentCreation(unittest.TestCase):
    """Test pricing agent creation and configuration."""

    def test_create_pricing_agent_returns_chat_agent(self):
        """Test that create_pricing_agent returns a ChatAgent instance."""
        mock_client = MagicMock()
        agent = create_pricing_agent(mock_client)
        
        # Verify agent was created with correct name
        self.assertEqual(agent.name, "pricing_agent")
    
    def test_create_pricing_agent_with_valid_client(self):
        """Test that pricing agent can be created with a mock client."""
        mock_client = MagicMock()
        agent = create_pricing_agent(mock_client)
        
        # Verify agent is not None
        self.assertIsNotNone(agent)
        
    def test_pricing_agent_name(self):
        """Test that the pricing agent has the correct name."""
        mock_client = MagicMock()
        agent = create_pricing_agent(mock_client)
        
        self.assertEqual(agent.name, "pricing_agent")


class TestPricingAgentIntegration(unittest.TestCase):
    """Integration tests for pricing agent (require running MCP server)."""
    
    @unittest.skip("Integration test - requires running MCP server at localhost:8080")
    def test_pricing_agent_can_connect_to_mcp(self):
        """Test that the agent can connect to the Azure Pricing MCP server."""
        # This test would require a running MCP server
        # Implement when doing integration testing
        pass


if __name__ == '__main__':
    unittest.main()