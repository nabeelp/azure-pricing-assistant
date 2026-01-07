"""Integration test for BOM Agent - Phase 2 Enhanced."""

import asyncio
import os

import pytest
from dotenv import load_dotenv
from azure.identity.aio import DefaultAzureCredential
from agent_framework_azure_ai import AzureAIAgentClient

from src.agents.bom_agent import create_bom_agent, parse_bom_response


RUN_LIVE = os.getenv("RUN_LIVE_BOM_INTEGRATION") == "1"


@pytest.mark.asyncio
async def test_bom_agent_simple_web_app():
    """
    Test BOM Agent with simple web app requirements.
    
    Expected: Should produce Azure App Service with appropriate SKU.
    """
    load_dotenv()
    
    if not RUN_LIVE:
        pytest.skip("Set RUN_LIVE_BOM_INTEGRATION=1 to run live BOM integration tests")

    endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    model = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
    if not endpoint or not model:
        pytest.skip("Missing AZURE_AI_PROJECT_ENDPOINT or AZURE_AI_MODEL_DEPLOYMENT_NAME")
    
    print("\n=== Test 1: Simple Web Application ===\n")
    
    requirements = """Requirements Summary:
- Workload Type: Web application
- Scale: 10,000 users per day
- Hosting Service: Azure App Service
- Deployment Region: East US
- Special Requirements: None (standard deployment)
"""
    
    async with DefaultAzureCredential() as credential:
        client = AzureAIAgentClient(
            project_endpoint=endpoint,
            model_deployment_name=model,
            credential=credential,
        )
        
        bom_agent = create_bom_agent(client)
        thread = bom_agent.get_new_thread()
        
        print("Requirements:")
        print(requirements)
        print("\nBOM Agent Response:")
        
        response = ""
        async for update in bom_agent.run_stream(requirements, thread=thread):
            if update.text:
                print(update.text, end='', flush=True)
                response += update.text
        
        print("\n\n=== Parsing and Validating BOM ===")
        
        try:
            bom_data = parse_bom_response(response)
            print(f"✅ Successfully parsed BOM with {len(bom_data)} items:")
            
            for item in bom_data:
                print(f"\n  Service: {item['serviceName']}")
                print(f"  SKU: {item['sku']}")
                print(f"  Quantity: {item['quantity']}")
                print(f"  Region: {item['region']} ({item['armRegionName']})")
                print(f"  Hours/Month: {item['hours_per_month']}")
            
            # Verify expected service
            assert len(bom_data) >= 1, "BOM should have at least 1 service"
            assert any("App Service" in item['serviceName'] for item in bom_data), \
                "BOM should include Azure App Service"
            
            # Verify region
            assert any(item['region'] == "East US" for item in bom_data), \
                "BOM should use East US region"
            assert any(item['armRegionName'] == "eastus" for item in bom_data), \
                "BOM should have correct ARM region name"
            
            print("\n✅ Test passed!")
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            raise


@pytest.mark.asyncio
async def test_bom_agent_database_workload():
    """
    Test BOM Agent with database requirements.
    
    Expected: Should produce SQL Database or Cosmos DB with appropriate SKU.
    """
    load_dotenv()
    
    if not RUN_LIVE:
        pytest.skip("Set RUN_LIVE_BOM_INTEGRATION=1 to run live BOM integration tests")

    endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    model = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
    if not endpoint or not model:
        pytest.skip("Missing AZURE_AI_PROJECT_ENDPOINT or AZURE_AI_MODEL_DEPLOYMENT_NAME")
    
    print("\n=== Test 2: Database Workload ===\n")
    
    requirements = """Requirements Summary:
- Workload Type: Database
- Database Type: SQL Database
- Data Size: 100 GB
- Transaction Volume: Medium (1000s of transactions per minute)
- Deployment Region: West US
- Special Requirements: None
"""
    
    async with DefaultAzureCredential() as credential:
        client = AzureAIAgentClient(
            project_endpoint=endpoint,
            model_deployment_name=model,
            credential=credential,
        )
        
        bom_agent = create_bom_agent(client)
        thread = bom_agent.get_new_thread()
        
        print("Requirements:")
        print(requirements)
        print("\nBOM Agent Response:")
        
        response = ""
        async for update in bom_agent.run_stream(requirements, thread=thread):
            if update.text:
                print(update.text, end='', flush=True)
                response += update.text
        
        print("\n\n=== Parsing and Validating BOM ===")
        
        try:
            bom_data = parse_bom_response(response)
            print(f"✅ Successfully parsed BOM with {len(bom_data)} items:")
            
            for item in bom_data:
                print(f"\n  Service: {item['serviceName']}")
                print(f"  SKU: {item['sku']}")
                print(f"  Quantity: {item['quantity']}")
                print(f"  Region: {item['region']} ({item['armRegionName']})")
                print(f"  Hours/Month: {item['hours_per_month']}")
            
            # Verify database service
            assert len(bom_data) >= 1, "BOM should have at least 1 service"
            assert any("SQL" in item['serviceName'] or "Database" in item['serviceName'] 
                      for item in bom_data), \
                "BOM should include a database service"
            
            # Verify region
            assert any("West US" in item['region'] for item in bom_data), \
                "BOM should use West US region"
            
            print("\n✅ Test passed!")
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            raise


@pytest.mark.asyncio
async def test_bom_agent_multi_service():
    """
    Test BOM Agent with multi-service requirements.
    
    Expected: Should produce multiple services (App Service + SQL + Storage).
    """
    load_dotenv()
    
    if not RUN_LIVE:
        pytest.skip("Set RUN_LIVE_BOM_INTEGRATION=1 to run live BOM integration tests")

    endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    model = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
    if not endpoint or not model:
        pytest.skip("Missing AZURE_AI_PROJECT_ENDPOINT or AZURE_AI_MODEL_DEPLOYMENT_NAME")
    
    print("\n=== Test 3: Multi-Service Solution ===\n")
    
    requirements = """Requirements Summary:
- Workload Type: Full-stack web application
- Services Needed:
  1. Azure App Service for web hosting
  2. SQL Database for data storage
  3. Azure Blob Storage for file storage
- Scale: 5,000 users per day
- Deployment Region: East US 2
- Special Requirements: None
"""
    
    async with DefaultAzureCredential() as credential:
        client = AzureAIAgentClient(
            project_endpoint=endpoint,
            model_deployment_name=model,
            credential=credential,
        )
        
        bom_agent = create_bom_agent(client)
        thread = bom_agent.get_new_thread()
        
        print("Requirements:")
        print(requirements)
        print("\nBOM Agent Response:")
        
        response = ""
        async for update in bom_agent.run_stream(requirements, thread=thread):
            if update.text:
                print(update.text, end='', flush=True)
                response += update.text
        
        print("\n\n=== Parsing and Validating BOM ===")
        
        try:
            bom_data = parse_bom_response(response)
            print(f"✅ Successfully parsed BOM with {len(bom_data)} items:")
            
            for item in bom_data:
                print(f"\n  Service: {item['serviceName']}")
                print(f"  SKU: {item['sku']}")
                print(f"  Quantity: {item['quantity']}")
                print(f"  Region: {item['region']} ({item['armRegionName']})")
                print(f"  Hours/Month: {item['hours_per_month']}")
            
            # Verify multiple services
            assert len(bom_data) >= 2, "BOM should have at least 2 services"
            
            service_names = [item['serviceName'] for item in bom_data]
            print(f"\n  Services included: {', '.join(service_names)}")
            
            # Verify all use same region
            regions = set(item['armRegionName'] for item in bom_data)
            assert len(regions) == 1, "All services should be in the same region"
            assert "eastus2" in regions, "Services should be in East US 2"
            
            print("\n✅ Test passed!")
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            raise


async def main():
    """Run all integration tests."""
    print("=" * 60)
    print("BOM Agent Integration Tests - Phase 2")
    print("=" * 60)
    
    try:
        await test_bom_agent_simple_web_app()
        await test_bom_agent_database_workload()
        await test_bom_agent_multi_service()
        
        print("\n" + "=" * 60)
        print("✅ All integration tests passed!")
        print("=" * 60)
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ Integration tests failed: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
