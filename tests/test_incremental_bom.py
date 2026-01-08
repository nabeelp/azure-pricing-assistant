"""Tests for incremental BOM building functionality."""

import pytest
from src.core.orchestrator import (
    should_trigger_bom_update,
    _merge_bom_items,
)


class TestBOMTriggerLogic:
    """Test BOM update trigger conditions."""

    def test_should_trigger_on_done(self):
        """Should trigger BOM update when conversation is done."""
        response_with_done = """
```json
{
    "requirements": "Web app in East US",
    "done": true
}
```
"""
        assert should_trigger_bom_update(response_with_done, 5) is True

    def test_should_trigger_on_service_mention(self):
        """Should trigger BOM update when services are mentioned."""
        responses = [
            "I recommend using Azure App Service for your web application.",
            "You'll need a SQL Database for your data storage.",
            "Let's set up a Virtual Machine with the Standard tier.",
            "We can use Azure Kubernetes Service (AKS) for container orchestration.",
        ]

        for response in responses:
            assert should_trigger_bom_update(response, 2) is True

    def test_should_trigger_every_3_turns(self):
        """Should trigger BOM update every 3 turns."""
        regular_response = "What region would you like to deploy to?"

        assert should_trigger_bom_update(regular_response, 3) is True
        assert should_trigger_bom_update(regular_response, 6) is True
        assert should_trigger_bom_update(regular_response, 9) is True

    def test_should_not_trigger_on_early_turns(self):
        """Should not trigger BOM update on early turns without service info."""
        regular_response = "What type of workload are you deploying?"

        assert should_trigger_bom_update(regular_response, 1) is False
        assert should_trigger_bom_update(regular_response, 2) is False

    def test_should_trigger_on_configuration_keywords(self):
        """Should trigger when configuration keywords are mentioned."""
        responses = [
            "We'll use the P1v2 SKU for better performance.",
            "The East US region would be good for your needs.",
            "Let's scale this to handle your workload.",
        ]

        for response in responses:
            assert should_trigger_bom_update(response, 2) is True


class TestBOMMerging:
    """Test BOM item merging logic."""

    def test_merge_new_item(self):
        """Should add a new item when it doesn't exist."""
        existing = [
            {
                "serviceName": "Azure App Service",
                "sku": "P1v2",
                "quantity": 1,
                "region": "East US",
                "armRegionName": "eastus",
                "hours_per_month": 730,
            }
        ]

        new = [
            {
                "serviceName": "SQL Database",
                "sku": "S1",
                "quantity": 1,
                "region": "East US",
                "armRegionName": "eastus",
                "hours_per_month": 730,
            }
        ]

        merged = _merge_bom_items(existing, new)

        assert len(merged) == 2
        assert merged[0]["serviceName"] == "Azure App Service"
        assert merged[1]["serviceName"] == "SQL Database"

    def test_merge_update_existing_item(self):
        """Should update existing item when service and region match."""
        existing = [
            {
                "serviceName": "Azure App Service",
                "sku": "B1",
                "quantity": 1,
                "region": "East US",
                "armRegionName": "eastus",
                "hours_per_month": 730,
            }
        ]

        new = [
            {
                "serviceName": "Azure App Service",
                "sku": "P1v2",
                "quantity": 2,
                "region": "East US",
                "armRegionName": "eastus",
                "hours_per_month": 730,
            }
        ]

        merged = _merge_bom_items(existing, new)

        assert len(merged) == 1
        assert merged[0]["sku"] == "P1v2"
        assert merged[0]["quantity"] == 2

    def test_merge_different_regions_as_separate(self):
        """Should keep items in different regions separate."""
        existing = [
            {
                "serviceName": "Azure App Service",
                "sku": "P1v2",
                "quantity": 1,
                "region": "East US",
                "armRegionName": "eastus",
                "hours_per_month": 730,
            }
        ]

        new = [
            {
                "serviceName": "Azure App Service",
                "sku": "P1v2",
                "quantity": 1,
                "region": "West US",
                "armRegionName": "westus",
                "hours_per_month": 730,
            }
        ]

        merged = _merge_bom_items(existing, new)

        assert len(merged) == 2
        assert merged[0]["region"] == "East US"
        assert merged[1]["region"] == "West US"

    def test_merge_empty_new_items(self):
        """Should return existing items when new items are empty."""
        existing = [
            {
                "serviceName": "Azure App Service",
                "sku": "P1v2",
                "quantity": 1,
                "region": "East US",
                "armRegionName": "eastus",
                "hours_per_month": 730,
            }
        ]

        merged = _merge_bom_items(existing, [])

        assert len(merged) == 1
        assert merged[0] == existing[0]

    def test_merge_multiple_updates(self):
        """Should handle multiple new items with both updates and additions."""
        existing = [
            {
                "serviceName": "Azure App Service",
                "sku": "B1",
                "quantity": 1,
                "region": "East US",
                "armRegionName": "eastus",
                "hours_per_month": 730,
            },
            {
                "serviceName": "SQL Database",
                "sku": "S1",
                "quantity": 1,
                "region": "East US",
                "armRegionName": "eastus",
                "hours_per_month": 730,
            },
        ]

        new = [
            {
                "serviceName": "Azure App Service",
                "sku": "P1v2",
                "quantity": 2,
                "region": "East US",
                "armRegionName": "eastus",
                "hours_per_month": 730,
            },
            {
                "serviceName": "Storage Account",
                "sku": "Standard_LRS",
                "quantity": 1,
                "region": "East US",
                "armRegionName": "eastus",
                "hours_per_month": 730,
            },
        ]

        merged = _merge_bom_items(existing, new)

        assert len(merged) == 3
        assert merged[0]["serviceName"] == "Azure App Service"
        assert merged[0]["sku"] == "P1v2"
        assert merged[1]["serviceName"] == "SQL Database"
        assert merged[2]["serviceName"] == "Storage Account"


class TestIncrementalBOMParsing:
    """Test BOM parsing in incremental mode."""

    def test_parse_empty_array_in_incremental_mode(self):
        """Test that empty arrays are accepted in incremental mode."""
        from src.agents.bom_agent import parse_bom_response

        response = """Based on the conversation so far, there is not enough information to create BOM items yet.
        
```json
[]
```"""

        # Should not raise when allow_empty=True
        result = parse_bom_response(response, allow_empty=True)
        assert result == []
        assert isinstance(result, list)

    def test_parse_empty_array_fails_in_standard_mode(self):
        """Test that empty arrays are rejected in standard mode."""
        from src.agents.bom_agent import parse_bom_response

        response = """```json
[]
```"""

        # Should raise when allow_empty=False (default)
        with pytest.raises(ValueError, match="cannot be empty"):
            parse_bom_response(response, allow_empty=False)
