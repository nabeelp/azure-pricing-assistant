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
        """Should trigger BOM update when services are mentioned in response."""
        responses = [
            "I recommend using Azure App Service for your web application.",
            "You'll need a SQL Database for your data storage.",
            "Let's set up a Virtual Machine with the Standard tier.",
            "We can use Azure Kubernetes Service (AKS) for container orchestration.",
        ]

        for response in responses:
            assert should_trigger_bom_update(response, 2) is True

    def test_should_trigger_on_service_mention_in_history(self):
        """Should trigger BOM update when services are mentioned in conversation history."""
        # Agent asks a question (no service keywords)
        response = "Which Azure region(s) are you targeting for deployment?"

        # But user mentioned service in history
        history = [
            {"role": "user", "content": "I want a web app"},
            {"role": "assistant", "content": response},
        ]

        assert should_trigger_bom_update(response, 2, history) is True

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


@pytest.mark.asyncio
class TestIncrementalBOMIntegration:
    """Integration tests for incremental BOM building with live agents.
    
    These tests require Azure credentials and are skipped by default.
    Set RUN_LIVE_BOM_INTEGRATION=1 to run them.
    """

    @pytest.fixture
    def client(self):
        """Create Azure AI Agent client from environment."""
        import os
        from agent_framework_azure_ai import AzureAIAgentClient

        endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
        if not endpoint:
            pytest.skip("AZURE_AI_PROJECT_ENDPOINT not set")

        return AzureAIAgentClient.from_env()

    @pytest.fixture
    def session_store(self):
        """Create in-memory session store."""
        from src.core.session import InMemorySessionStore

        return InMemorySessionStore()

    async def test_incremental_bom_multi_turn_conversation(self, client, session_store):
        """Test BOM is updated incrementally across multiple conversation turns."""
        import os

        if not os.getenv("RUN_LIVE_BOM_INTEGRATION"):
            pytest.skip("Set RUN_LIVE_BOM_INTEGRATION=1 to run integration tests")

        from src.core.orchestrator import run_question_turn

        session_id = "test-session-001"

        # Turn 1: User mentions web app
        result = await run_question_turn(
            client,
            session_store,
            session_id,
            "I need a web application",
            enable_incremental_bom=True,
        )

        assert "response" in result
        assert "is_done" in result

        # Check BOM after turn 1 (may be empty or have initial item)
        session = session_store.get(session_id)
        assert session is not None
        initial_bom = session.bom_items or []
        print(f"Turn 1 BOM: {len(initial_bom)} items")

        # Turn 2: User specifies region and scale
        result = await run_question_turn(
            client, session_store, session_id, "East US region, for 1000 daily users"
        )

        # BOM should have at least one item by now
        session = session_store.get(session_id)
        bom_after_2 = session.bom_items or []
        print(f"Turn 2 BOM: {len(bom_after_2)} items")

        # Turn 3: User adds database
        result = await run_question_turn(
            client, session_store, session_id, "I also need a SQL database"
        )

        # BOM should now have multiple items
        session = session_store.get(session_id)
        bom_after_3 = session.bom_items or []
        print(f"Turn 3 BOM: {len(bom_after_3)} items")
        assert len(bom_after_3) >= len(bom_after_2), "BOM should grow or stay same"

        # Turn 4: User changes SKU for web app
        result = await run_question_turn(
            client, session_store, session_id, "Actually, use Premium P1v2 tier for the web app"
        )

        # BOM should have updated the web app SKU
        session = session_store.get(session_id)
        final_bom = session.bom_items or []
        print(f"Final BOM: {len(final_bom)} items")

        # Verify BOM structure
        for item in final_bom:
            assert "serviceName" in item
            assert "sku" in item
            assert "quantity" in item
            assert "region" in item
            assert "armRegionName" in item
            assert "hours_per_month" in item

        # Verify we captured the web app with updated tier
        web_app_items = [
            item for item in final_bom if "app service" in item["serviceName"].lower()
        ]
        if web_app_items:
            assert any("p1v2" in item["sku"].lower() for item in web_app_items), (
                "Web app should have P1v2 SKU"
            )

    async def test_bom_merge_updates_existing_item(self, client, session_store):
        """Test that BOM merge correctly updates existing items."""
        import os

        if not os.getenv("RUN_LIVE_BOM_INTEGRATION"):
            pytest.skip("Set RUN_LIVE_BOM_INTEGRATION=1 to run integration tests")

        from src.core.orchestrator import run_question_turn

        session_id = "test-session-002"

        # First mention of VM
        await run_question_turn(
            client,
            session_store,
            session_id,
            "I need a virtual machine with Basic tier in East US",
            enable_incremental_bom=True,
        )

        session = session_store.get(session_id)
        initial_bom = session.bom_items or []
        initial_count = len(initial_bom)

        # Update VM to Standard tier
        await run_question_turn(
            client,
            session_store,
            session_id,
            "Actually change the VM to Standard D4s_v3 tier",
        )

        session = session_store.get(session_id)
        updated_bom = session.bom_items or []

        # Should not add a new item, just update existing
        assert len(updated_bom) == initial_count, (
            "BOM count should stay same when updating existing service"
        )

        # Verify VM was updated to Standard tier
        vm_items = [
            item
            for item in updated_bom
            if "virtual machine" in item["serviceName"].lower()
            or "compute" in item["serviceName"].lower()
        ]
        if vm_items:
            # At least one VM item should have Standard SKU
            assert any("standard" in item["sku"].lower() for item in vm_items), (
                "VM should have Standard SKU"
            )

    async def test_bom_complete_after_done_signal(self, client, session_store):
        """Test BOM is finalized when conversation reaches done=true."""
        import os

        if not os.getenv("RUN_LIVE_BOM_INTEGRATION"):
            pytest.skip("Set RUN_LIVE_BOM_INTEGRATION=1 to run integration tests")

        from src.core.orchestrator import run_question_turn

        session_id = "test-session-003"

        # Simulate quick conversation
        await run_question_turn(
            client,
            session_store,
            session_id,
            "Web app in East US, SQL database, 1000 users",
            enable_incremental_bom=True,
        )

        # Multiple turns to build context
        for i in range(2):
            result = await run_question_turn(
                client,
                session_store,
                session_id,
                "Yes, that sounds good",
            )
            if result.get("is_done"):
                break

        # Verify BOM is present
        session = session_store.get(session_id)
        final_bom = session.bom_items or []

        # BOM should have items by now
        assert len(final_bom) > 0, "BOM should have items after conversation"

        # Verify BOM items have required fields
        for item in final_bom:
            assert item.get("serviceName"), f"Missing serviceName: {item}"
            assert item.get("sku"), f"Missing sku: {item}"
            assert item.get("region"), f"Missing region: {item}"
            assert item.get("armRegionName"), f"Missing armRegionName: {item}"

    async def test_bom_handles_multi_region_deployment(self, client, session_store):
        """Test BOM correctly handles services deployed in multiple regions."""
        import os

        if not os.getenv("RUN_LIVE_BOM_INTEGRATION"):
            pytest.skip("Set RUN_LIVE_BOM_INTEGRATION=1 to run integration tests")

        from src.core.orchestrator import run_question_turn

        session_id = "test-session-004"

        # Request multi-region deployment
        await run_question_turn(
            client,
            session_store,
            session_id,
            "I need web apps in both East US and West Europe regions",
            enable_incremental_bom=True,
        )

        # Add more context
        await run_question_turn(
            client, session_store, session_id, "Premium P1v2 tier for both"
        )

        # Check BOM has separate items for each region
        session = session_store.get(session_id)
        bom = session.bom_items or []

        regions_found = {item.get("region") for item in bom}
        print(f"Regions in BOM: {regions_found}")

        # Should have items for multiple regions (at least 2)
        assert len(regions_found) >= 2, "Should have services in multiple regions"

    async def test_incremental_bom_with_disabled_flag(self, client, session_store):
        """Test that BOM is not updated when enable_incremental_bom=False."""
        import os

        if not os.getenv("RUN_LIVE_BOM_INTEGRATION"):
            pytest.skip("Set RUN_LIVE_BOM_INTEGRATION=1 to run integration tests")

        from src.core.orchestrator import run_question_turn

        session_id = "test-session-005"

        # Run with incremental BOM disabled
        await run_question_turn(
            client,
            session_store,
            session_id,
            "I need a web application in East US",
            enable_incremental_bom=False,
        )

        # BOM should remain empty
        session = session_store.get(session_id)
        bom = session.bom_items or []
        assert len(bom) == 0, "BOM should be empty when incremental BOM is disabled"
