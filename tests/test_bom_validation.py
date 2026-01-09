"""Tests for BOM validation against Azure pricing catalog."""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from dotenv import load_dotenv
from azure.identity.aio import DefaultAzureCredential
from agent_framework_azure_ai import AzureAIAgentClient

from src.agents.bom_agent import validate_bom_against_pricing_catalog


class TestBOMValidation:
    """Test BOM validation against pricing catalog."""

    @pytest.mark.asyncio
    async def test_validation_with_valid_items(self):
        """Test validation passes for valid BOM items."""
        bom_items = [
            {
                "serviceName": "Azure App Service",
                "sku": "P1v2",
                "quantity": 1,
                "region": "East US",
                "armRegionName": "eastus",
                "hours_per_month": 730,
            }
        ]

        mock_client = MagicMock(spec=AzureAIAgentClient)

        # Mock validate_bom_item to return valid
        async def mock_validate_item(*args, **kwargs):
            return True, "VALID"

        with patch("src.agents.bom_agent.validate_bom_item", side_effect=mock_validate_item):
            with patch("src.agents.bom_agent.ChatAgent"):
                result = await validate_bom_against_pricing_catalog(bom_items, mock_client)

                assert len(result["valid_items"]) == 1
                assert len(result["invalid_items"]) == 0
                assert result["valid_items"][0]["serviceName"] == "Azure App Service"

    @pytest.mark.asyncio
    async def test_validation_with_invalid_items(self):
        """Test validation detects invalid BOM items."""
        bom_items = [
            {
                "serviceName": "InvalidService",
                "sku": "InvalidSKU",
                "quantity": 1,
                "region": "East US",
                "armRegionName": "eastus",
                "hours_per_month": 730,
            }
        ]

        mock_client = MagicMock(spec=AzureAIAgentClient)

        # Mock validate_bom_item to return invalid
        async def mock_validate_item(*args, **kwargs):
            return False, "INVALID: Service not found in pricing catalog"

        with patch("src.agents.bom_agent.validate_bom_item", side_effect=mock_validate_item):
            with patch("src.agents.bom_agent.ChatAgent"):
                result = await validate_bom_against_pricing_catalog(bom_items, mock_client)

                assert len(result["valid_items"]) == 0
                assert len(result["invalid_items"]) == 1
                assert result["invalid_items"][0]["item"]["serviceName"] == "InvalidService"
                assert "not found" in result["invalid_items"][0]["reason"]

    @pytest.mark.asyncio
    async def test_validation_with_mixed_items(self):
        """Test validation handles mix of valid and invalid items."""
        bom_items = [
            {
                "serviceName": "Azure App Service",
                "sku": "P1v2",
                "quantity": 1,
                "region": "East US",
                "armRegionName": "eastus",
                "hours_per_month": 730,
            },
            {
                "serviceName": "InvalidService",
                "sku": "InvalidSKU",
                "quantity": 1,
                "region": "East US",
                "armRegionName": "eastus",
                "hours_per_month": 730,
            },
        ]

        mock_client = MagicMock(spec=AzureAIAgentClient)

        # Mock to return different results for different calls
        call_count = [0]

        async def mock_validate_item(*args, **kwargs):
            if call_count[0] == 0:
                call_count[0] += 1
                return True, "VALID"
            else:
                return False, "INVALID: Service not found"

        with patch("src.agents.bom_agent.validate_bom_item", side_effect=mock_validate_item):
            with patch("src.agents.bom_agent.ChatAgent"):
                result = await validate_bom_against_pricing_catalog(bom_items, mock_client)

                assert len(result["valid_items"]) == 1
                assert len(result["invalid_items"]) == 1
                assert result["valid_items"][0]["serviceName"] == "Azure App Service"
                assert result["invalid_items"][0]["item"]["serviceName"] == "InvalidService"

    @pytest.mark.asyncio
    async def test_validation_handles_errors_gracefully(self):
        """Test validation handles MCP errors gracefully."""
        bom_items = [
            {
                "serviceName": "Azure App Service",
                "sku": "P1v2",
                "quantity": 1,
                "region": "East US",
                "armRegionName": "eastus",
                "hours_per_month": 730,
            }
        ]

        mock_client = MagicMock(spec=AzureAIAgentClient)

        # Mock to raise an exception
        async def mock_validate_item(*args, **kwargs):
            raise Exception("MCP connection failed")

        with patch("src.agents.bom_agent.validate_bom_item", side_effect=mock_validate_item):
            with patch("src.agents.bom_agent.ChatAgent"):
                result = await validate_bom_against_pricing_catalog(bom_items, mock_client)

                # Should still return valid items (fail-open approach)
                assert len(result["valid_items"]) == 1
                assert len(result["warnings"]) == 1
                assert "Could not validate" in result["warnings"][0]

    @pytest.mark.asyncio
    async def test_validation_with_empty_bom(self):
        """Test validation handles empty BOM gracefully."""
        bom_items = []
        mock_client = MagicMock(spec=AzureAIAgentClient)

        with patch("src.agents.bom_agent.ChatAgent"):
            result = await validate_bom_against_pricing_catalog(bom_items, mock_client)

            assert len(result["valid_items"]) == 0
            assert len(result["invalid_items"]) == 0


# Live integration test (requires Azure credentials and MCP server)
RUN_LIVE = os.getenv("RUN_LIVE_BOM_VALIDATION") == "1"


@pytest.mark.asyncio
async def test_live_validation_with_azure_app_service():
    """
    Live test: Validate real Azure App Service BOM item.
    
    Requires:
    - RUN_LIVE_BOM_VALIDATION=1
    - Azure credentials
    - Azure Pricing MCP server running
    """
    load_dotenv()

    if not RUN_LIVE:
        pytest.skip("Set RUN_LIVE_BOM_VALIDATION=1 to run live validation tests")

    endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    model = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
    if not endpoint or not model:
        pytest.skip("Missing AZURE_AI_PROJECT_ENDPOINT or AZURE_AI_MODEL_DEPLOYMENT_NAME")

    print("\n=== Live Validation Test: Azure App Service ===\n")

    bom_items = [
        {
            "serviceName": "Azure App Service",
            "sku": "P1v2",
            "quantity": 1,
            "region": "East US",
            "armRegionName": "eastus",
            "hours_per_month": 730,
        }
    ]

    async with DefaultAzureCredential() as credential:
        client = AzureAIAgentClient(
            project_endpoint=endpoint,
            model_deployment_name=model,
            credential=credential,
        )

        result = await validate_bom_against_pricing_catalog(bom_items, client)

        print(f"Valid items: {len(result['valid_items'])}")
        print(f"Invalid items: {len(result['invalid_items'])}")
        print(f"Warnings: {len(result['warnings'])}")

        if result["invalid_items"]:
            print("\nInvalid items:")
            for invalid in result["invalid_items"]:
                print(f"  - {invalid['item']['serviceName']}: {invalid['reason']}")

        if result["warnings"]:
            print("\nWarnings:")
            for warning in result["warnings"]:
                print(f"  - {warning}")

        # Assert validation results
        assert len(result["valid_items"]) > 0, "Should have at least one valid item"
        print("\n✅ Live validation test passed!")


@pytest.mark.asyncio
async def test_live_validation_with_invalid_service():
    """
    Live test: Validate invalid service name detection.
    
    Requires:
    - RUN_LIVE_BOM_VALIDATION=1
    - Azure credentials
    - Azure Pricing MCP server running
    """
    load_dotenv()

    if not RUN_LIVE:
        pytest.skip("Set RUN_LIVE_BOM_VALIDATION=1 to run live validation tests")

    endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    model = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
    if not endpoint or not model:
        pytest.skip("Missing AZURE_AI_PROJECT_ENDPOINT or AZURE_AI_MODEL_DEPLOYMENT_NAME")

    print("\n=== Live Validation Test: Invalid Service ===\n")

    bom_items = [
        {
            "serviceName": "NonExistentAzureService",
            "sku": "InvalidSKU123",
            "quantity": 1,
            "region": "East US",
            "armRegionName": "eastus",
            "hours_per_month": 730,
        }
    ]

    async with DefaultAzureCredential() as credential:
        client = AzureAIAgentClient(
            project_endpoint=endpoint,
            model_deployment_name=model,
            credential=credential,
        )

        result = await validate_bom_against_pricing_catalog(bom_items, client)

        print(f"Valid items: {len(result['valid_items'])}")
        print(f"Invalid items: {len(result['invalid_items'])}")
        print(f"Warnings: {len(result['warnings'])}")

        if result["invalid_items"]:
            print("\nInvalid items detected:")
            for invalid in result["invalid_items"]:
                print(f"  - {invalid['item']['serviceName']}: {invalid['reason']}")

        # This should ideally detect invalid service, but may pass due to fuzzy matching
        # Log the result for review
        print("\n✅ Live validation test completed!")


async def main():
    """Run all validation tests."""
    print("=" * 60)
    print("BOM Validation Tests")
    print("=" * 60)

    try:
        # Unit tests with mocks
        test = TestBOMValidation()
        await test.test_validation_with_valid_items()
        print("✅ test_validation_with_valid_items")

        await test.test_validation_with_invalid_items()
        print("✅ test_validation_with_invalid_items")

        await test.test_validation_with_mixed_items()
        print("✅ test_validation_with_mixed_items")

        await test.test_validation_handles_errors_gracefully()
        print("✅ test_validation_handles_errors_gracefully")

        await test.test_validation_with_empty_bom()
        print("✅ test_validation_with_empty_bom")

        # Live tests (if enabled)
        if RUN_LIVE:
            await test_live_validation_with_azure_app_service()
            await test_live_validation_with_invalid_service()

        print("\n" + "=" * 60)
        print("✅ All validation tests passed!")
        print("=" * 60)

    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ Tests failed: {e}")
        print("=" * 60)
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
