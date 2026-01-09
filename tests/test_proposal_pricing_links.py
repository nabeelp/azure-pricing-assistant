"""Tests for pricing links in proposal agent instructions and generated proposals."""

import re
import pytest

from src.agents.proposal_agent import create_proposal_agent


class TestProposalAgentInstructions:
    """Test that proposal agent instructions include pricing link guidance."""

    def test_proposal_agent_source_includes_pricing_link_guidance(self):
        """Test that agent instructions explicitly mention pricing links."""
        import inspect
        
        # Get source code of create_proposal_agent function
        source = inspect.getsource(create_proposal_agent)
        
        # Verify instructions mention pricing links
        assert "pricing_url" in source or "pricing page" in source.lower()
        assert "markdown link" in source.lower()
        assert "azure.microsoft.com/pricing" in source

    def test_proposal_agent_source_provides_examples(self):
        """Test that agent instructions provide pricing link examples."""
        import inspect
        
        # Get source code of create_proposal_agent function
        source = inspect.getsource(create_proposal_agent)
        
        # Verify examples of pricing links are provided
        assert "Virtual Machines" in source
        assert "App Service" in source or "Azure SQL Database" in source
        assert "[" in source and "](" in source  # Markdown link syntax

    def test_proposal_cost_breakdown_instructions_mention_links(self):
        """Test that Cost Breakdown instructions specifically require links."""
        import inspect
        
        source = inspect.getsource(create_proposal_agent)
        
        # Verify Cost Breakdown section instructions include link requirements
        assert "Cost Breakdown" in source
        # The table format should show service names as links
        assert "Service Name" in source or "[Service" in source or "pricing_url" in source


class TestProposalLinkFormatRequirements:
    """Test pricing link format requirements in instructions."""

    def test_instructions_require_https_links(self):
        """Test that instructions specify HTTPS URLs."""
        import inspect
        
        source = inspect.getsource(create_proposal_agent)
        
        # Extract URLs from instructions
        url_pattern = r'https://[^\s\)]+'
        urls = re.findall(url_pattern, source)
        
        # Verify all Azure pricing URLs use HTTPS
        azure_pricing_urls = [url for url in urls if "azure.microsoft.com/pricing" in url]
        assert len(azure_pricing_urls) > 0
        for url in azure_pricing_urls:
            assert url.startswith("https://")

    def test_instructions_show_pricing_details_format(self):
        """Test that instructions show pricing/details/{service}/ format."""
        import inspect
        
        source = inspect.getsource(create_proposal_agent)
        
        # Verify format: https://azure.microsoft.com/pricing/details/{service}/
        expected_patterns = [
            r'https://azure\.microsoft\.com/pricing/details/[\w-]+/',
            r'https://azure\.microsoft\.com/pricing/calculator/',
        ]
        
        url_pattern = r'https://[^\s\)]+'
        urls = re.findall(url_pattern, source)
        azure_urls = [url for url in urls if "azure.microsoft.com/pricing" in url]
        
        # At least one URL should match expected format
        matches_format = False
        for url in azure_urls:
            for pattern in expected_patterns:
                if re.match(pattern, url):
                    matches_format = True
                    break
        
        assert matches_format, f"No URLs match expected format. Found: {azure_urls}"

    def test_instructions_include_multiple_service_examples(self):
        """Test that instructions include examples for multiple services."""
        import inspect
        
        source = inspect.getsource(create_proposal_agent)
        
        # Check for at least 2 different service examples
        common_services = [
            "Virtual Machines",
            "App Service",
            "Azure SQL Database",
            "Storage",
            "Cosmos DB",
            "Functions",
        ]
        
        found_services = [svc for svc in common_services if svc in source]
        assert len(found_services) >= 2, f"Expected at least 2 service examples, found: {found_services}"


class TestProposalPricingLinkContent:
    """Test that generated proposals will contain pricing links."""

    def test_cost_breakdown_table_format_includes_service_links(self):
        """Test that Cost Breakdown table format expects service name links."""
        import inspect
        
        source = inspect.getsource(create_proposal_agent)
        
        # Find Cost Breakdown section
        assert "## Cost Breakdown" in source
        
        # The instructions should show format with links
        # Looking for [[Service Name](pricing_url)] pattern in example
        assert "pricing_url" in source or "[Service" in source


class TestProposalPricingURLUtility:
    """Test that pricing URL utility module exists and works."""

    def test_pricing_url_utility_exists(self):
        """Test that azure_pricing_urls utility module exists."""
        from src.shared import azure_pricing_urls
        
        assert hasattr(azure_pricing_urls, "get_pricing_url_for_service")
        assert hasattr(azure_pricing_urls, "format_service_with_pricing_link")

    def test_pricing_url_utility_has_service_mappings(self):
        """Test that utility has common service mappings."""
        from src.shared.azure_pricing_urls import SERVICE_NAME_TO_PRICING_URL
        
        assert "Virtual Machines" in SERVICE_NAME_TO_PRICING_URL
        assert "App Service" in SERVICE_NAME_TO_PRICING_URL
        assert len(SERVICE_NAME_TO_PRICING_URL) >= 10  # Should have at least 10 services
