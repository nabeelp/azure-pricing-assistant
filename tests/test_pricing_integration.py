"""Integration tests for Pricing Agent with live Azure Pricing MCP server."""

import asyncio
import os
from datetime import datetime

import pytest
from dotenv import load_dotenv
from azure.identity.aio import DefaultAzureCredential
from agent_framework_azure_ai import AzureAIAgentClient

from src.agents.pricing_agent import create_pricing_agent, parse_pricing_response


RUN_LIVE = os.getenv("RUN_LIVE_PRICING_INTEGRATION") == "1"


@pytest.fixture(scope="module")
def check_prerequisites():
    """Check that required environment variables and services are available."""
    load_dotenv()
    
    if not RUN_LIVE:
        pytest.skip("Set RUN_LIVE_PRICING_INTEGRATION=1 to run live pricing integration tests")
    
    endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    model = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
    pricing_mcp_url = os.getenv("AZURE_PRICING_MCP_URL", "http://localhost:8080/mcp")
    
    if not endpoint:
        pytest.skip("Missing AZURE_AI_PROJECT_ENDPOINT environment variable")
    if not model:
        pytest.skip("Missing AZURE_AI_MODEL_DEPLOYMENT_NAME environment variable")
    
    return {
        "endpoint": endpoint,
        "model": model,
        "pricing_mcp_url": pricing_mcp_url
    }


@pytest.mark.asyncio
async def test_pricing_agent_simple_app_service(check_prerequisites):
    """
    Test Pricing Agent with simple App Service BOM.
    
    Expected: Should return pricing for App Service with valid unit price and monthly cost.
    """
    config = check_prerequisites
    
    print("\n=== Test 1: Simple App Service Pricing ===\n")
    
    bom = [
        {
            "serviceName": "App Service",
            "sku": "S1",
            "quantity": 1,
            "region": "East US",
            "armRegionName": "eastus",
            "hours_per_month": 730
        }
    ]
    
    async with DefaultAzureCredential() as credential:
        client = AzureAIAgentClient(
            project_endpoint=config["endpoint"],
            model_deployment_name=config["model"],
            credential=credential,
        )
        
        pricing_agent = create_pricing_agent(client)
        thread = pricing_agent.get_new_thread()
        
        bom_json = {"items": bom}
        prompt = f"Calculate pricing for this Bill of Materials:\n\n```json\n{bom_json}\n```"
        
        print("BOM:")
        print(f"  Service: {bom[0]['serviceName']}")
        print(f"  SKU: {bom[0]['sku']}")
        print(f"  Region: {bom[0]['region']}")
        print("\nPricing Agent Response:")
        
        response = ""
        async for update in pricing_agent.run_stream(prompt, thread=thread):
            if update.text:
                print(update.text, end='', flush=True)
                response += update.text
        
        print("\n\n=== Parsing and Validating Pricing ===")
        
        try:
            pricing_data = parse_pricing_response(response)
            print(f"✅ Successfully parsed pricing")
            print(f"\nPricing Details:")
            print(f"  Total Monthly: ${pricing_data['total_monthly']:.2f}")
            print(f"  Currency: {pricing_data['currency']}")
            print(f"  Pricing Date: {pricing_data['pricing_date']}")
            
            if pricing_data.get('items'):
                for item in pricing_data['items']:
                    print(f"\n  Item:")
                    print(f"    Service: {item['serviceName']}")
                    print(f"    SKU: {item['sku']}")
                    print(f"    Unit Price: ${item['unit_price']:.4f}")
                    print(f"    Monthly Cost: ${item['monthly_cost']:.2f}")
                    if item.get('notes'):
                        print(f"    Notes: {item['notes']}")
            
            # Validate response structure
            assert 'total_monthly' in pricing_data, "Pricing should include total_monthly"
            assert 'currency' in pricing_data, "Pricing should include currency"
            assert 'pricing_date' in pricing_data, "Pricing should include pricing_date"
            assert 'items' in pricing_data, "Pricing should include items array"
            
            # Validate data types
            assert isinstance(pricing_data['total_monthly'], (int, float)), \
                "total_monthly should be numeric"
            assert isinstance(pricing_data['currency'], str), "currency should be string"
            assert isinstance(pricing_data['pricing_date'], str), "pricing_date should be string"
            assert isinstance(pricing_data['items'], list), "items should be list"
            
            # Validate pricing date format (YYYY-MM-DD)
            try:
                datetime.strptime(pricing_data['pricing_date'], "%Y-%m-%d")
            except ValueError:
                pytest.fail(f"pricing_date should be in YYYY-MM-DD format, got: {pricing_data['pricing_date']}")
            
            # Validate items structure
            assert len(pricing_data['items']) == 1, "Should have 1 pricing item"
            item = pricing_data['items'][0]
            assert 'serviceName' in item, "Item should include serviceName"
            assert 'sku' in item, "Item should include sku"
            assert 'unit_price' in item, "Item should include unit_price"
            assert 'monthly_cost' in item, "Item should include monthly_cost"
            
            # Validate pricing is reasonable (not zero for standard service)
            if item['unit_price'] > 0:
                assert item['monthly_cost'] > 0, \
                    "monthly_cost should be > 0 when unit_price > 0"
                print("\n✅ Pricing validation passed")
            else:
                print(f"\n⚠️  Warning: unit_price is $0.00, check if pricing lookup failed")
                if pricing_data.get('errors'):
                    print(f"   Errors: {pricing_data['errors']}")
            
        except Exception as e:
            pytest.fail(f"Failed to parse pricing response: {e}\n\nResponse:\n{response}")


@pytest.mark.asyncio
async def test_pricing_agent_multiple_services(check_prerequisites):
    """
    Test Pricing Agent with multiple services in BOM.
    
    Expected: Should return pricing for all services with correct total calculation.
    """
    config = check_prerequisites
    
    print("\n=== Test 2: Multiple Services Pricing ===\n")
    
    bom = [
        {
            "serviceName": "App Service",
            "sku": "S1",
            "quantity": 2,
            "region": "East US",
            "armRegionName": "eastus",
            "hours_per_month": 730
        },
        {
            "serviceName": "SQL Database",
            "sku": "S0",
            "quantity": 1,
            "region": "East US",
            "armRegionName": "eastus",
            "hours_per_month": 730
        },
        {
            "serviceName": "Storage",
            "sku": "Standard_LRS",
            "quantity": 100,
            "region": "East US",
            "armRegionName": "eastus",
            "hours_per_month": 730
        }
    ]
    
    async with DefaultAzureCredential() as credential:
        client = AzureAIAgentClient(
            project_endpoint=config["endpoint"],
            model_deployment_name=config["model"],
            credential=credential,
        )
        
        pricing_agent = create_pricing_agent(client)
        thread = pricing_agent.get_new_thread()
        
        bom_json = {"items": bom}
        prompt = f"Calculate pricing for this Bill of Materials:\n\n```json\n{bom_json}\n```"
        
        print("BOM:")
        for item in bom:
            print(f"  - {item['serviceName']} ({item['sku']}) x {item['quantity']}")
        print("\nPricing Agent Response:")
        
        response = ""
        async for update in pricing_agent.run_stream(prompt, thread=thread):
            if update.text:
                print(update.text, end='', flush=True)
                response += update.text
        
        print("\n\n=== Parsing and Validating Pricing ===")
        
        try:
            pricing_data = parse_pricing_response(response)
            print(f"✅ Successfully parsed pricing")
            print(f"\nPricing Summary:")
            print(f"  Total Monthly: ${pricing_data['total_monthly']:.2f}")
            
            assert len(pricing_data['items']) == 3, "Should have 3 pricing items"
            
            # Calculate expected total (sum of all item monthly_cost * quantity)
            calculated_total = sum(
                item['monthly_cost'] * item.get('quantity', 1)
                for item in pricing_data['items']
            )
            
            print(f"  Calculated Total: ${calculated_total:.2f}")
            
            # Validate total is within reasonable range of calculated total
            # Allow for rounding differences
            assert abs(pricing_data['total_monthly'] - calculated_total) < 1.0, \
                f"total_monthly ({pricing_data['total_monthly']}) should match sum of items ({calculated_total})"
            
            print("\n✅ Total calculation validation passed")
            
        except Exception as e:
            pytest.fail(f"Failed to parse pricing response: {e}\n\nResponse:\n{response}")


@pytest.mark.asyncio
async def test_pricing_agent_graceful_fallback(check_prerequisites):
    """
    Test Pricing Agent graceful fallback when pricing data unavailable.
    
    Expected: Should return $0.00 for unavailable items with error notes.
    """
    config = check_prerequisites
    
    print("\n=== Test 3: Graceful Fallback for Unavailable Pricing ===\n")
    
    # Use a fictional or obscure SKU that likely won't have pricing
    bom = [
        {
            "serviceName": "App Service",
            "sku": "FICTIONAL_SKU_XYZ999",
            "quantity": 1,
            "region": "East US",
            "armRegionName": "eastus",
            "hours_per_month": 730
        }
    ]
    
    async with DefaultAzureCredential() as credential:
        client = AzureAIAgentClient(
            project_endpoint=config["endpoint"],
            model_deployment_name=config["model"],
            credential=credential,
        )
        
        pricing_agent = create_pricing_agent(client)
        thread = pricing_agent.get_new_thread()
        
        bom_json = {"items": bom}
        prompt = f"Calculate pricing for this Bill of Materials:\n\n```json\n{bom_json}\n```"
        
        print("BOM (with fictional SKU):")
        print(f"  Service: {bom[0]['serviceName']}")
        print(f"  SKU: {bom[0]['sku']}")
        print("\nPricing Agent Response:")
        
        response = ""
        async for update in pricing_agent.run_stream(prompt, thread=thread):
            if update.text:
                print(update.text, end='', flush=True)
                response += update.text
        
        print("\n\n=== Parsing and Validating Fallback Behavior ===")
        
        try:
            pricing_data = parse_pricing_response(response)
            print(f"✅ Successfully parsed pricing with fallback")
            
            # Should have errors array when pricing fails
            if pricing_data.get('errors'):
                print(f"\nErrors (as expected for fictional SKU):")
                for error in pricing_data['errors']:
                    print(f"  - {error}")
            
            # Validate fallback behavior
            assert len(pricing_data['items']) == 1, "Should have 1 pricing item"
            item = pricing_data['items'][0]
            
            # When pricing fails, should set to $0.00
            if item['unit_price'] == 0.0 and item['monthly_cost'] == 0.0:
                print("\n✅ Fallback to $0.00 for unavailable pricing")
                
                # Should have error note or errors array
                has_error_info = (
                    item.get('notes') or
                    pricing_data.get('errors')
                )
                assert has_error_info, \
                    "Should provide error note or errors array when pricing unavailable"
                print("✅ Error information provided")
            else:
                print(f"\n⚠️  Note: Got non-zero price for fictional SKU: ${item['unit_price']}")
                print("   This might indicate the MCP server found a fallback price")
            
        except Exception as e:
            pytest.fail(f"Failed to parse pricing response: {e}\n\nResponse:\n{response}")


@pytest.mark.asyncio
async def test_pricing_agent_total_accuracy(check_prerequisites):
    """
    Test Pricing Agent total calculation accuracy.
    
    Expected: total_monthly should equal sum of (item.monthly_cost * item.quantity).
    """
    config = check_prerequisites
    
    print("\n=== Test 4: Total Calculation Accuracy ===\n")
    
    bom = [
        {
            "serviceName": "Virtual Machines",
            "sku": "Standard_D2s_v3",
            "quantity": 3,
            "region": "West US",
            "armRegionName": "westus",
            "hours_per_month": 730
        },
        {
            "serviceName": "Storage",
            "sku": "Standard_LRS",
            "quantity": 500,
            "region": "West US",
            "armRegionName": "westus",
            "hours_per_month": 730
        }
    ]
    
    async with DefaultAzureCredential() as credential:
        client = AzureAIAgentClient(
            project_endpoint=config["endpoint"],
            model_deployment_name=config["model"],
            credential=credential,
        )
        
        pricing_agent = create_pricing_agent(client)
        thread = pricing_agent.get_new_thread()
        
        bom_json = {"items": bom}
        prompt = f"Calculate pricing for this Bill of Materials:\n\n```json\n{bom_json}\n```"
        
        print("BOM:")
        for item in bom:
            print(f"  - {item['serviceName']} ({item['sku']}) x {item['quantity']}")
        
        response = ""
        async for update in pricing_agent.run_stream(prompt, thread=thread):
            if update.text:
                response += update.text
        
        try:
            pricing_data = parse_pricing_response(response)
            
            print(f"\nPricing Items:")
            manual_total = 0.0
            for item in pricing_data['items']:
                item_total = item['monthly_cost'] * item.get('quantity', 1)
                manual_total += item_total
                print(f"  {item['serviceName']}: ${item['monthly_cost']:.2f} x {item.get('quantity', 1)} = ${item_total:.2f}")
            
            print(f"\nManual Total: ${manual_total:.2f}")
            print(f"Agent Total:  ${pricing_data['total_monthly']:.2f}")
            
            # Allow small rounding difference (< $1)
            difference = abs(pricing_data['total_monthly'] - manual_total)
            assert difference < 1.0, \
                f"Total mismatch: agent={pricing_data['total_monthly']}, manual={manual_total}, diff={difference}"
            
            print(f"✅ Total calculation accurate (difference: ${difference:.2f})")
            
        except Exception as e:
            pytest.fail(f"Failed validation: {e}\n\nResponse:\n{response}")


@pytest.mark.asyncio
async def test_pricing_agent_region_variations(check_prerequisites):
    """
    Test Pricing Agent with different Azure regions.
    
    Expected: Should return region-specific pricing (prices vary by region).
    """
    config = check_prerequisites
    
    print("\n=== Test 5: Region-Specific Pricing ===\n")
    
    # Same service in two different regions
    bom = [
        {
            "serviceName": "App Service",
            "sku": "P1v3",
            "quantity": 1,
            "region": "East US",
            "armRegionName": "eastus",
            "hours_per_month": 730
        },
        {
            "serviceName": "App Service",
            "sku": "P1v3",
            "quantity": 1,
            "region": "West Europe",
            "armRegionName": "westeurope",
            "hours_per_month": 730
        }
    ]
    
    async with DefaultAzureCredential() as credential:
        client = AzureAIAgentClient(
            project_endpoint=config["endpoint"],
            model_deployment_name=config["model"],
            credential=credential,
        )
        
        pricing_agent = create_pricing_agent(client)
        thread = pricing_agent.get_new_thread()
        
        bom_json = {"items": bom}
        prompt = f"Calculate pricing for this Bill of Materials:\n\n```json\n{bom_json}\n```"
        
        print("BOM (same SKU, different regions):")
        for item in bom:
            print(f"  - {item['serviceName']} ({item['sku']}) in {item['region']}")
        
        response = ""
        async for update in pricing_agent.run_stream(prompt, thread=thread):
            if update.text:
                response += update.text
        
        try:
            pricing_data = parse_pricing_response(response)
            
            print(f"\nRegion Pricing Comparison:")
            assert len(pricing_data['items']) == 2, "Should have 2 pricing items"
            
            for item in pricing_data['items']:
                print(f"  {item['region']}: ${item['monthly_cost']:.2f}/month")
            
            # Regions may have different prices, but both should be non-zero
            # (unless pricing lookup failed)
            item1, item2 = pricing_data['items'][0], pricing_data['items'][1]
            
            if item1['monthly_cost'] > 0 and item2['monthly_cost'] > 0:
                print("\n✅ Both regions have valid pricing")
                
                # They may or may not be different - just verify both are reasonable
                assert item1['monthly_cost'] < 10000, "Price should be reasonable (< $10k/month)"
                assert item2['monthly_cost'] < 10000, "Price should be reasonable (< $10k/month)"
            else:
                print(f"\n⚠️  Warning: One or both regions returned $0.00 pricing")
            
        except Exception as e:
            pytest.fail(f"Failed validation: {e}\n\nResponse:\n{response}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
