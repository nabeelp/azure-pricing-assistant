"""Integration tests for Proposal generation workflow: BOM → Pricing → Proposal."""

import os
from datetime import datetime

import pytest
from dotenv import load_dotenv
from azure.identity.aio import DefaultAzureCredential
from agent_framework_azure_ai import AzureAIAgentClient

from src.agents.bom_agent import create_bom_agent, parse_bom_response
from src.agents.pricing_agent import create_pricing_agent, parse_pricing_response
from src.agents.proposal_agent import create_proposal_agent


RUN_LIVE = os.getenv("RUN_LIVE_PROPOSAL_WORKFLOW") == "1"


@pytest.fixture(scope="module")
def check_prerequisites():
    """Check that required environment variables and services are available."""
    load_dotenv()
    
    if not RUN_LIVE:
        pytest.skip("Set RUN_LIVE_PROPOSAL_WORKFLOW=1 to run live proposal workflow tests")
    
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
async def test_proposal_workflow_simple_web_app(check_prerequisites):
    """
    Test complete workflow: BOM → Pricing → Proposal for simple web app.
    
    Expected: Proposal should include all BOM items, costs should match pricing, markdown should be client-ready.
    """
    config = check_prerequisites
    
    print("\n=== Test 1: Simple Web App Proposal Workflow ===\n")
    
    # Define requirements for BOM generation
    requirements = """
Requirements Summary:
- Workload Type: Web application  
- Target Audience: 5,000 daily active users
- Hosting Service: Azure App Service
- Database: Azure SQL Database for application data
- Deployment Region: East US
- Availability: 24/7 operation
- Performance Tier: Standard/Production-ready
"""
    
    async with DefaultAzureCredential() as credential:
        client = AzureAIAgentClient(
            project_endpoint=config["endpoint"],
            model_deployment_name=config["model"],
            credential=credential,
        )
        
        # ===== PHASE 1: BOM Generation =====
        print("PHASE 1: BOM Agent - Generate Bill of Materials")
        print("-" * 80)
        
        bom_agent = create_bom_agent(client)
        bom_thread = bom_agent.get_new_thread()
        
        print(f"Requirements: {requirements[:100]}...\n")
        
        bom_response = ""
        async for update in bom_agent.run_stream(requirements, thread=bom_thread):
            if update.text:
                bom_response += update.text
        
        print("BOM Agent Response:\n" + bom_response[:500] + "...\n")
        
        # Parse BOM
        bom_data = parse_bom_response(bom_response)
        print(f"✅ BOM parsed: {len(bom_data)} services")
        for item in bom_data:
            print(f"  - {item['serviceName']} ({item['sku']}) x{item['quantity']} in {item['region']}")
        
        # Validate BOM structure
        assert len(bom_data) >= 2, "BOM should have at least 2 services (App Service + SQL)"
        for item in bom_data:
            assert 'serviceName' in item, "BOM item should have serviceName"
            assert 'sku' in item, "BOM item should have sku"
            assert 'region' in item, "BOM item should have region"
            assert 'armRegionName' in item, "BOM item should have armRegionName"
            assert 'quantity' in item, "BOM item should have quantity"
            assert 'hours_per_month' in item, "BOM item should have hours_per_month"
        
        # ===== PHASE 2: Pricing Calculation =====
        print("\n\nPHASE 2: Pricing Agent - Calculate Costs")
        print("-" * 80)
        
        pricing_agent = create_pricing_agent(client)
        pricing_thread = pricing_agent.get_new_thread()
        
        # Pass BOM to pricing agent
        bom_json = {"items": bom_data}
        pricing_prompt = f"Calculate pricing for this Bill of Materials:\n\n```json\n{bom_json}\n```"
        
        pricing_response = ""
        async for update in pricing_agent.run_stream(pricing_prompt, thread=pricing_thread):
            if update.text:
                pricing_response += update.text
        
        print("Pricing Agent Response:\n" + pricing_response[:500] + "...\n")
        
        # Parse pricing
        pricing_data = parse_pricing_response(pricing_response)
        print(f"✅ Pricing parsed:")
        print(f"  Total Monthly: ${pricing_data['total_monthly']:.2f}")
        print(f"  Currency: {pricing_data['currency']}")
        print(f"  Pricing Date: {pricing_data['pricing_date']}")
        print(f"  Items: {len(pricing_data['items'])}")
        
        for item in pricing_data['items']:
            print(f"  - {item['serviceName']}: ${item['monthly_cost']:.2f}/mo")
        
        # Validate pricing structure
        assert 'total_monthly' in pricing_data, "Pricing should have total_monthly"
        assert 'currency' in pricing_data, "Pricing should have currency"
        assert 'pricing_date' in pricing_data, "Pricing should have pricing_date"
        assert 'items' in pricing_data, "Pricing should have items"
        assert len(pricing_data['items']) == len(bom_data), \
            "Pricing should have same number of items as BOM"
        
        # ===== PHASE 3: Proposal Generation =====
        print("\n\nPHASE 3: Proposal Agent - Generate Professional Proposal")
        print("-" * 80)
        
        proposal_agent = create_proposal_agent(client)
        proposal_thread = proposal_agent.get_new_thread()
        
        # Pass requirements, BOM, and pricing to proposal agent
        proposal_prompt = f"""
{requirements}

Bill of Materials:
{bom_response}

Pricing Analysis:
{pricing_response}
"""
        
        proposal_text = ""
        async for update in proposal_agent.run_stream(proposal_prompt, thread=proposal_thread):
            if update.text:
                proposal_text += update.text
        
        print("\n\nProposal Agent Response (first 1000 chars):")
        print(proposal_text[:1000] + "...\n")
        
        # ===== VALIDATION =====
        print("\nValidating Proposal...")
        print("-" * 80)
        
        # 1. Verify proposal includes all BOM items
        print("\n1. Checking all BOM items are mentioned in proposal...")
        for item in bom_data:
            service_name = item['serviceName']
            assert service_name in proposal_text, \
                f"Proposal should mention BOM service: {service_name}"
            print(f"  ✅ {service_name} mentioned")
        
        # 2. Verify proposal costs match pricing output
        print("\n2. Checking costs match pricing output...")
        total_str = f"${pricing_data['total_monthly']:.2f}"
        # The proposal might format costs slightly differently, so check for the amount
        total_amount = pricing_data['total_monthly']
        # Check if any formatting of the total appears (with or without commas)
        assert (total_str in proposal_text or 
                f"${total_amount:,.2f}" in proposal_text or
                str(int(total_amount)) in proposal_text), \
            f"Proposal should mention total cost: ${total_amount}"
        print(f"  ✅ Total cost ${total_amount:.2f} mentioned")
        
        # Check individual item costs
        for item in pricing_data['items']:
            if item['monthly_cost'] > 0:
                cost_amount = item['monthly_cost']
                # Check if cost appears in some form
                assert (f"${cost_amount:.2f}" in proposal_text or
                        f"${cost_amount:,.2f}" in proposal_text or
                        str(int(cost_amount)) in proposal_text), \
                    f"Proposal should mention cost for {item['serviceName']}: ${cost_amount}"
                print(f"  ✅ {item['serviceName']} cost ${cost_amount:.2f} mentioned")
        
        # 3. Verify proposal markdown is client-ready
        print("\n3. Checking proposal format is client-ready...")
        
        # Should have key sections
        assert "Executive Summary" in proposal_text or "Summary" in proposal_text, \
            "Proposal should have Executive Summary section"
        print("  ✅ Has Executive Summary")
        
        assert "Solution Architecture" in proposal_text or "Architecture" in proposal_text, \
            "Proposal should have Solution Architecture section"
        print("  ✅ Has Solution Architecture")
        
        assert "Cost Breakdown" in proposal_text or "Pricing" in proposal_text or "Cost" in proposal_text, \
            "Proposal should have Cost Breakdown section"
        print("  ✅ Has Cost Breakdown")
        
        assert "Total Cost Summary" in proposal_text or "Total" in proposal_text, \
            "Proposal should have Total Cost Summary"
        print("  ✅ Has Total Cost Summary")
        
        assert "Next Steps" in proposal_text or "Recommendations" in proposal_text, \
            "Proposal should have Next Steps section"
        print("  ✅ Has Next Steps")
        
        # Should be professional and well-formatted
        assert len(proposal_text) > 500, "Proposal should have substantial content (>500 chars)"
        print(f"  ✅ Has substantial content ({len(proposal_text)} chars)")
        
        assert proposal_text.count("#") >= 3, "Proposal should have proper markdown headers"
        print(f"  ✅ Has proper markdown structure ({proposal_text.count('#')} headers)")
        
        # Should not have placeholders or incomplete sections
        placeholder_phrases = ["[TBD]", "[TODO]", "TODO:", "FIXME:", "XXX", "placeholder"]
        for phrase in placeholder_phrases:
            assert phrase not in proposal_text, f"Proposal should not contain placeholder: {phrase}"
        print("  ✅ No placeholders or TODOs")
        
        # Should mention the pricing date
        assert pricing_data['pricing_date'] in proposal_text or \
               datetime.strptime(pricing_data['pricing_date'], "%Y-%m-%d").strftime("%B %d, %Y") in proposal_text, \
            "Proposal should mention pricing date"
        print("  ✅ Mentions pricing date")
        
        print("\n" + "=" * 80)
        print("✅ ALL VALIDATIONS PASSED")
        print("=" * 80)
        print("\nProposal Workflow Test Summary:")
        print(f"  - BOM Items: {len(bom_data)}")
        print(f"  - Pricing Items: {len(pricing_data['items'])}")
        print(f"  - Total Monthly Cost: ${pricing_data['total_monthly']:.2f} {pricing_data['currency']}")
        print(f"  - Proposal Length: {len(proposal_text)} characters")
        print(f"  - All BOM items included: ✅")
        print(f"  - All costs accurate: ✅")
        print(f"  - Client-ready format: ✅")


@pytest.mark.asyncio
async def test_proposal_workflow_multi_region(check_prerequisites):
    """
    Test proposal workflow with multi-region deployment.
    
    Expected: Proposal should handle multiple regions correctly.
    """
    config = check_prerequisites
    
    print("\n=== Test 2: Multi-Region Proposal Workflow ===\n")
    
    requirements = """
Requirements Summary:
- Workload Type: Global web application with geo-distribution
- Hosting: Azure App Service in two regions for redundancy
- Primary Region: East US
- Secondary Region: West Europe
- Database: Azure SQL Database (geo-replicated)
- Expected Traffic: 10,000 users per day globally
"""
    
    async with DefaultAzureCredential() as credential:
        client = AzureAIAgentClient(
            project_endpoint=config["endpoint"],
            model_deployment_name=config["model"],
            credential=credential,
        )
        
        # BOM Generation
        print("Generating BOM...")
        bom_agent = create_bom_agent(client)
        bom_thread = bom_agent.get_new_thread()
        
        bom_response = ""
        async for update in bom_agent.run_stream(requirements, thread=bom_thread):
            if update.text:
                bom_response += update.text
        
        bom_data = parse_bom_response(bom_response)
        print(f"✅ BOM: {len(bom_data)} services across multiple regions")
        
        # Verify multi-region BOM
        regions = set(item['region'] for item in bom_data)
        print(f"  Regions: {', '.join(regions)}")
        
        # Pricing Calculation
        print("\nCalculating pricing...")
        pricing_agent = create_pricing_agent(client)
        pricing_thread = pricing_agent.get_new_thread()
        
        bom_json = {"items": bom_data}
        pricing_prompt = f"Calculate pricing for this Bill of Materials:\n\n```json\n{bom_json}\n```"
        
        pricing_response = ""
        async for update in pricing_agent.run_stream(pricing_prompt, thread=pricing_thread):
            if update.text:
                pricing_response += update.text
        
        pricing_data = parse_pricing_response(pricing_response)
        print(f"✅ Pricing: ${pricing_data['total_monthly']:.2f}/month total")
        
        # Proposal Generation
        print("\nGenerating proposal...")
        proposal_agent = create_proposal_agent(client)
        proposal_thread = proposal_agent.get_new_thread()
        
        proposal_prompt = f"""
{requirements}

Bill of Materials:
{bom_response}

Pricing Analysis:
{pricing_response}
"""
        
        proposal_text = ""
        async for update in proposal_agent.run_stream(proposal_prompt, thread=proposal_thread):
            if update.text:
                proposal_text += update.text
        
        print("\nValidating multi-region proposal...")
        
        # Should mention both regions
        assert len(regions) >= 2, "Should have resources in at least 2 regions"
        for region in regions:
            assert region in proposal_text, f"Proposal should mention {region}"
            print(f"  ✅ {region} mentioned")
        
        # Should explain multi-region architecture
        multi_region_terms = ["redundancy", "geo", "failover", "distributed", "global", "availability"]
        has_multi_region_discussion = any(term in proposal_text.lower() for term in multi_region_terms)
        assert has_multi_region_discussion, "Proposal should discuss multi-region architecture benefits"
        print("  ✅ Discusses multi-region architecture")
        
        print("\n✅ Multi-region proposal workflow test passed")


@pytest.mark.asyncio
async def test_proposal_workflow_with_pricing_errors(check_prerequisites):
    """
    Test proposal workflow when some pricing data is unavailable.
    
    Expected: Proposal should gracefully handle missing pricing and note it.
    """
    config = check_prerequisites
    
    print("\n=== Test 3: Proposal Workflow with Pricing Errors ===\n")
    
    # Create a BOM with a fictional SKU that likely won't have pricing
    requirements = """
Requirements Summary:
- Workload Type: Specialized application
- Custom Service Configuration: Fictional SKU for testing error handling
- Region: East US
"""
    
    async with DefaultAzureCredential() as credential:
        client = AzureAIAgentClient(
            project_endpoint=config["endpoint"],
            model_deployment_name=config["model"],
            credential=credential,
        )
        
        # Use a predefined BOM with fictional SKU
        bom_data = [
            {
                "serviceName": "App Service",
                "sku": "FICTIONAL_TEST_SKU_XYZ",
                "quantity": 1,
                "region": "East US",
                "armRegionName": "eastus",
                "hours_per_month": 730
            }
        ]
        
        print("Using BOM with fictional SKU...")
        
        # Pricing (should return $0.00 with error)
        print("\nAttempting pricing calculation...")
        pricing_agent = create_pricing_agent(client)
        pricing_thread = pricing_agent.get_new_thread()
        
        bom_json = {"items": bom_data}
        pricing_prompt = f"Calculate pricing for this Bill of Materials:\n\n```json\n{bom_json}\n```"
        
        pricing_response = ""
        async for update in pricing_agent.run_stream(pricing_prompt, thread=pricing_thread):
            if update.text:
                pricing_response += update.text
        
        pricing_data = parse_pricing_response(pricing_response)
        print(f"✅ Pricing response received (graceful fallback expected)")
        
        # Should have errors array or $0.00 prices
        has_errors = pricing_data.get('errors') is not None
        has_zero_prices = any(item['monthly_cost'] == 0 for item in pricing_data['items'])
        
        if has_errors:
            print(f"  Errors: {pricing_data['errors']}")
        if has_zero_prices:
            print("  Some items have $0.00 pricing")
        
        # Proposal Generation
        print("\nGenerating proposal with pricing fallback...")
        proposal_agent = create_proposal_agent(client)
        proposal_thread = proposal_agent.get_new_thread()
        
        proposal_prompt = f"""
{requirements}

Bill of Materials:
{{"items": {bom_data}}}

Pricing Analysis:
{pricing_response}
"""
        
        proposal_text = ""
        async for update in proposal_agent.run_stream(proposal_prompt, thread=proposal_thread):
            if update.text:
                proposal_text += update.text
        
        print("\nValidating error-handling proposal...")
        
        # Proposal should note pricing unavailability
        pricing_unavailable_phrases = [
            "pricing unavailable",
            "pricing not available",
            "contact",
            "estimate",
            "$0",
            "TBD",
            "to be determined"
        ]
        
        has_pricing_note = any(phrase.lower() in proposal_text.lower() 
                               for phrase in pricing_unavailable_phrases)
        assert has_pricing_note, \
            "Proposal should note when pricing is unavailable"
        print("  ✅ Notes pricing unavailability")
        
        # Should still have proper structure
        assert "Executive Summary" in proposal_text or "Summary" in proposal_text
        print("  ✅ Has proper structure despite pricing errors")
        
        print("\n✅ Error handling proposal workflow test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
