"""End-to-End Workflow Test - Complete Question → BOM → Pricing → Proposal flow."""

import asyncio
import os

import pytest
from dotenv import load_dotenv
from azure.identity.aio import DefaultAzureCredential
from agent_framework_azure_ai import AzureAIAgentClient

from src.agents.question_agent import create_question_agent
from src.agents.bom_agent import create_bom_agent, parse_bom_response
from src.agents.pricing_agent import create_pricing_agent, parse_pricing_response
from src.agents.proposal_agent import create_proposal_agent
from src.core.orchestrator import parse_question_completion


RUN_LIVE_E2E = os.getenv("RUN_LIVE_E2E") == "1"


@pytest.mark.asyncio
async def test_e2e_simple_web_app():
    """
    End-to-End Test: Simple Web Application Scenario
    
    Complete workflow: Question Agent → BOM Agent → Pricing Agent → Proposal Agent
    
    Expected flow:
    - Question Agent gathers requirements
    - BOM Agent produces bill of materials
    - Pricing Agent calculates costs
    - Proposal Agent generates professional proposal
    """
    load_dotenv()
    
    if not RUN_LIVE_E2E:
        pytest.skip("Set RUN_LIVE_E2E=1 to run live E2E workflow tests")

    endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    model = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
    if not endpoint or not model:
        pytest.skip("Missing AZURE_AI_PROJECT_ENDPOINT or AZURE_AI_MODEL_DEPLOYMENT_NAME")
    
    print("\n" + "=" * 80)
    print("E2E TEST 1: Simple Web Application")
    print("=" * 80 + "\n")
    
    async with DefaultAzureCredential() as credential:
        client = AzureAIAgentClient(
            project_endpoint=endpoint,
            model_deployment_name=model,
            credential=credential,
        )
        
        # ===== PHASE 1: Question Agent - Gather Requirements =====
        print("PHASE 1: Question Agent - Gathering Requirements")
        print("-" * 80)
        
        question_agent = create_question_agent(client)
        question_thread = question_agent.get_new_thread()
        
        # Simulate user interaction
        user_input = "I need to build a web application that serves 5,000 users daily with peak loads"
        print(f"User: {user_input}\n")
        
        response_text = ""
        async for update in question_agent.run_stream(user_input, thread=question_thread):
            if update.text:
                response_text += update.text
                print(update.text, end='', flush=True)
        
        # Verify completion format
        is_done, requirements = parse_question_completion(response_text)
        
        if not is_done:
            # Continue conversation if more info needed
            user_input2 = "I'll deploy to East US, use Azure App Service, SQL Database for data, and we need 50GB of storage"
            print(f"\nUser: {user_input2}\n")
            
            response_text = ""
            async for update in question_agent.run_stream(user_input2, thread=question_thread):
                if update.text:
                    response_text += update.text
                    print(update.text, end='', flush=True)
            
            is_done, requirements = parse_question_completion(response_text)
        
        assert is_done, "Question Agent should return done=true"
        assert requirements, "Requirements should be extracted"
        print(f"\n✅ Requirements gathered: {requirements[:100]}...\n")
        
        # ===== PHASE 2: BOM Agent - Generate Bill of Materials =====
        print("\nPHASE 2: BOM Agent - Generating Bill of Materials")
        print("-" * 80)
        
        bom_agent = create_bom_agent(client)
        bom_thread = bom_agent.get_new_thread()
        
        print(f"Requirements input: {requirements}\n")
        
        bom_response = ""
        async for update in bom_agent.run_stream(requirements, thread=bom_thread):
            if update.text:
                bom_response += update.text
                print(update.text, end='', flush=True)
        
        # Parse and validate BOM
        print("\n\nValidating BOM schema...")
        bom_data = parse_bom_response(bom_response)
        
        assert isinstance(bom_data, list), "BOM should be an array"
        assert len(bom_data) >= 1, "BOM should have at least 1 service"
        
        print(f"✅ BOM schema valid: {len(bom_data)} services")
        for item in bom_data:
            assert "serviceName" in item, "BOM item missing serviceName"
            assert "sku" in item, "BOM item missing sku"
            assert "region" in item, "BOM item missing region"
            assert "armRegionName" in item, "BOM item missing armRegionName"
            assert "quantity" in item, "BOM item missing quantity"
            assert "hours_per_month" in item, "BOM item missing hours_per_month"
            print(f"  - {item['serviceName']} ({item['sku']}): {item['quantity']}x in {item['region']}")
        
        # ===== PHASE 3: Pricing Agent - Calculate Costs =====
        print("\n\nPHASE 3: Pricing Agent - Calculating Costs")
        print("-" * 80)
        
        pricing_agent = create_pricing_agent(client)
        pricing_thread = pricing_agent.get_new_thread()
        
        # Format BOM for pricing agent
        bom_text = f"Bill of Materials:\n{bom_response}"
        print(f"BOM input to Pricing Agent: {bom_text[:200]}...\n")
        
        pricing_response = ""
        async for update in pricing_agent.run_stream(bom_text, thread=pricing_thread):
            if update.text:
                pricing_response += update.text
                print(update.text, end='', flush=True)
        
        # Parse and validate pricing
        print("\n\nValidating pricing schema...")
        pricing_result = parse_pricing_response(pricing_response)
        
        assert isinstance(pricing_result, dict), "Pricing result should be a dict"
        assert "items" in pricing_result, "Pricing missing items array"
        assert "total_monthly" in pricing_result, "Pricing missing total_monthly"
        assert "currency" in pricing_result, "Pricing missing currency"
        assert "pricing_date" in pricing_result, "Pricing missing pricing_date"
        
        items = pricing_result["items"]
        assert len(items) >= 1, "Pricing should have at least 1 item"
        
        print(f"✅ Pricing schema valid:")
        print(f"  - Items: {len(items)}")
        print(f"  - Currency: {pricing_result['currency']}")
        print(f"  - Date: {pricing_result['pricing_date']}")
        print(f"  - Total Monthly: ${pricing_result['total_monthly']:.2f}")
        
        for item in items:
            assert "serviceName" in item, "Pricing item missing serviceName"
            assert "unit_price" in item, "Pricing item missing unit_price"
            assert "monthly_cost" in item, "Pricing item missing monthly_cost"
            assert "pricing_date" in pricing_result, "Missing pricing_date"
            print(f"  - {item['serviceName']}: ${item['monthly_cost']:.2f}/mo")
        
        # ===== PHASE 4: Proposal Agent - Generate Proposal =====
        print("\n\nPHASE 4: Proposal Agent - Generating Proposal")
        print("-" * 80)
        
        proposal_agent = create_proposal_agent(client)
        proposal_thread = proposal_agent.get_new_thread()
        
        # Format requirements + BOM + pricing for proposal
        proposal_input = f"""
Requirements: {requirements}

Bill of Materials:
{bom_response}

Pricing Analysis:
{pricing_response}
"""
        
        proposal_text = ""
        async for update in proposal_agent.run_stream(proposal_input, thread=proposal_thread):
            if update.text:
                proposal_text += update.text
                print(update.text, end='', flush=True)
        
        # Validate proposal
        print("\n\nValidating proposal format...")
        assert len(proposal_text) > 0, "Proposal should have content"
        assert "Executive Summary" in proposal_text or "Summary" in proposal_text, \
            "Proposal should have executive summary"
        assert "Cost" in proposal_text or "$" in proposal_text, \
            "Proposal should mention costs"
        
        print(f"✅ Proposal generated successfully ({len(proposal_text)} chars)")
        print(f"  - Contains cost information: {'$' in proposal_text}")
        print(f"  - Contains summary: {'Summary' in proposal_text}")
        
        print("\n" + "=" * 80)
        print("✅ E2E TEST 1 PASSED: Complete workflow successful")
        print("=" * 80)


@pytest.mark.asyncio
async def test_e2e_database_workload():
    """
    End-to-End Test: Database Workload Scenario
    
    Tests the full workflow with a different scenario to ensure robustness.
    """
    load_dotenv()
    
    if not RUN_LIVE_E2E:
        pytest.skip("Set RUN_LIVE_E2E=1 to run live E2E workflow tests")

    endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    model = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
    if not endpoint or not model:
        pytest.skip("Missing AZURE_AI_PROJECT_ENDPOINT or AZURE_AI_MODEL_DEPLOYMENT_NAME")
    
    print("\n" + "=" * 80)
    print("E2E TEST 2: Database Workload")
    print("=" * 80 + "\n")
    
    async with DefaultAzureCredential() as credential:
        client = AzureAIAgentClient(
            project_endpoint=endpoint,
            model_deployment_name=model,
            credential=credential,
        )
        
        # Question Agent
        question_agent = create_question_agent(client)
        question_thread = question_agent.get_new_thread()
        
        user_input = "I need to set up a data warehouse in Azure with 200GB of data, deployed in West US"
        print(f"User: {user_input}\n")
        
        response_text = ""
        async for update in question_agent.run_stream(user_input, thread=question_thread):
            if update.text:
                response_text += update.text
                print(update.text, end='', flush=True)
        
        is_done, requirements = parse_question_completion(response_text)
        assert is_done, "Question Agent should complete"
        print(f"\n✅ Requirements gathered\n")
        
        # BOM Agent
        bom_agent = create_bom_agent(client)
        bom_response = ""
        async for update in bom_agent.run_stream(requirements, thread=bom_agent.get_new_thread()):
            if update.text:
                bom_response += update.text
        
        bom_data = parse_bom_response(bom_response)
        assert len(bom_data) >= 1, "BOM should have services"
        print(f"✅ BOM generated: {len(bom_data)} services\n")
        
        # Pricing Agent
        pricing_agent = create_pricing_agent(client)
        pricing_response = ""
        async for update in pricing_agent.run_stream(bom_response, thread=pricing_agent.get_new_thread()):
            if update.text:
                pricing_response += update.text
        
        pricing_result = parse_pricing_response(pricing_response)
        assert "total_monthly" in pricing_result, "Pricing should have total"
        print(f"✅ Pricing calculated: ${pricing_result['total_monthly']:.2f}/mo\n")
        
        # Proposal Agent
        proposal_agent = create_proposal_agent(client)
        proposal_text = ""
        async for update in proposal_agent.run_stream(
            f"Requirements: {requirements}\n\nBOM: {bom_response}\n\nPricing: {pricing_response}",
            thread=proposal_agent.get_new_thread()
        ):
            if update.text:
                proposal_text += update.text
        
        assert len(proposal_text) > 0, "Proposal should be generated"
        print(f"✅ Proposal generated\n")
        
        print("=" * 80)
        print("✅ E2E TEST 2 PASSED: Database workload workflow successful")
        print("=" * 80)


async def main():
    """Run all E2E workflow tests."""
    print("=" * 80)
    print("END-TO-END WORKFLOW TESTS")
    print("=" * 80)
    
    try:
        await test_e2e_simple_web_app()
        await test_e2e_database_workload()
        
        print("\n" + "=" * 80)
        print("✅ ALL E2E TESTS PASSED!")
        print("=" * 80)
        
    except Exception as e:
        print("\n" + "=" * 80)
        print(f"❌ E2E TESTS FAILED: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())
