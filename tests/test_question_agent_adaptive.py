"""Tests for adaptive questioning strategy in Question Agent."""

import pytest

from src.core.orchestrator import parse_question_completion


def test_parse_completion_with_environment_and_availability():
    """Should extract requirements including environment type and availability requirements."""
    response = """```json
{
  "requirements": "Workload: web application; Region: East US; Environment: Production; Availability: High availability with zone redundancy; Services: App Service, SQL Database; Scale: 5000 users",
  "done": true
}
```"""

    done, requirements = parse_question_completion(response)

    assert done is True
    assert "Environment: Production" in requirements
    assert "Availability: High availability" in requirements
    assert "Region: East US" in requirements


def test_parse_completion_with_dev_environment():
    """Should handle dev environment type in requirements."""
    response = """```json
{
  "requirements": "Workload: database; Region: West US; Environment: Development; Availability: Standard deployment; Services: Azure SQL Database (Basic tier); Scale: 10GB test data",
  "done": true
}
```"""

    done, requirements = parse_question_completion(response)

    assert done is True
    assert "Environment: Development" in requirements
    assert "Availability: Standard deployment" in requirements


def test_parse_completion_with_multiple_regions():
    """Should handle multiple target regions in requirements."""
    response = """```json
{
  "requirements": "Workload: global web app; Region: East US, West Europe, Southeast Asia; Environment: Production; Availability: Multi-region active-active; Services: Azure Front Door, App Service, Cosmos DB; Scale: 100k users globally",
  "done": true
}
```"""

    done, requirements = parse_question_completion(response)

    assert done is True
    assert "East US, West Europe, Southeast Asia" in requirements
    assert "Multi-region active-active" in requirements


def test_parse_completion_with_qa_environment():
    """Should handle QA/testing environment type in requirements."""
    response = """```json
{
  "requirements": "Workload: ML pipeline; Region: Central US; Environment: QA/Testing; Availability: Standard; Services: Azure Machine Learning, Storage Account; Scale: Medium model training workload",
  "done": true
}
```"""

    done, requirements = parse_question_completion(response)

    assert done is True
    assert "Environment: QA/Testing" in requirements or "Environment: QA" in requirements


def test_parse_completion_comprehensive_requirements():
    """Should handle comprehensive requirements with all new fields."""
    response = """```json
{
  "requirements": "Workload: e-commerce web application; Region: East US; Environment: Production; Availability: High availability with zone redundancy and disaster recovery to West US; Services: App Service (P1v3), Azure SQL Database (Business Critical tier), Application Insights, Azure Front Door, Key Vault; Scale: 10,000 daily users, peak 1000 req/min; Database: ~50GB, read-heavy workload; Additional: PCI-DSS compliance required",
  "done": true
}
```"""

    done, requirements = parse_question_completion(response)

    assert done is True
    assert "Workload: e-commerce" in requirements
    assert "Region: East US" in requirements
    assert "Environment: Production" in requirements
    assert "Availability: High availability" in requirements
    assert "disaster recovery" in requirements
    assert "Services: App Service" in requirements
    assert "Scale: 10,000 daily users" in requirements


def test_incomplete_response_not_done():
    """Should return done=False when agent is still asking questions."""
    response = """Thank you for that information. To help size the solution appropriately, 
which Azure region are you targeting for deployment?"""

    done, requirements = parse_question_completion(response)

    assert done is False


def test_json_without_code_block_fallback():
    """Should handle JSON even without code block wrapper (with warning)."""
    response = """Based on our conversation, here are your requirements:
{"requirements": "Workload: web app; Region: East US; Environment: Production; Availability: Standard; Services: App Service; Scale: 5000 users", "done": true}"""

    done, requirements = parse_question_completion(response)

    # Should still work but logs a warning
    assert done is True
    assert "Workload: web app" in requirements
    assert "Region: East US" in requirements


def test_agent_instructions_include_numbered_options():
    """Verify that agent instructions include numbered options guidance."""
    from src.agents.question_agent import create_question_agent

    # Mock client
    class MockClient:
        pass

    mock_client = MockClient()
    agent = create_question_agent(mock_client)

    # Get instructions from the function source since agent doesn't expose them
    import inspect

    source = inspect.getsource(create_question_agent)

    # Check for numbered options guidance
    assert "NUMBERED OPTIONS FOR EASY SELECTION" in source
    assert "Users can respond with just the number" in source
    assert "OR with full text" in source
    assert "1. " in source

    # Check for proper formatting instructions (each option on new line)
    assert "Each option MUST be on a NEW LINE" in source or "each on new line" in source
    assert "each on its own line" in source or "NEW LINE for readability" in source

    # Check for examples in adaptive sequence
    assert "Development/Testing" in source
    assert "QA/Staging" in source
    assert "Zone-redundant" in source
    assert "Region-redundant" in source


def test_agent_instructions_include_architecture_based_questioning():
    """Verify that agent instructions include architecture-based questioning guidance."""
    from src.agents.question_agent import create_question_agent
    import inspect

    # Mock client
    class MockClient:
        pass

    mock_client = MockClient()
    agent = create_question_agent(mock_client)

    # Get instructions from the function source
    source = inspect.getsource(create_question_agent)

    # Check for architecture-based questioning section
    assert "ARCHITECTURE-BASED QUESTIONING" in source
    assert "recommended Azure architecture" in source or "recommended architecture" in source
    
    # Check for instructions to search for architectures
    assert "microsoft_docs_search to look up" in source or "microsoft_docs_search to find" in source
    assert "reference architecture" in source or "Azure Well-Architected Framework" in source
    
    # Check for architecture-specific questions examples
    assert "private networking" in source or "VNet integration" in source
    assert "Application Gateway" in source or "application gateway" in source
    
    # Check for security-related architecture questions
    assert "WAF" in source or "Web Application Firewall" in source
    assert "private endpoints" in source
    
    # Check that architecture components are included in completion criteria
    assert "Architecture components" in source or "architecture components" in source
    
    # Verify example shows architecture in requirements
    assert "Architecture:" in source  # Should be in the example JSON


def test_parse_completion_with_architecture_components():
    """Should extract requirements including architecture components."""
    response = """```json
{
  "requirements": "Workload: e-commerce web application; Region: East US; Environment: Production; Availability: High availability with zone redundancy; Architecture: Private VNet with Application Gateway and WAF, private endpoints for database; Services: App Service (P1v3), Azure SQL Database; Scale: 10,000 daily users",
  "done": true
}
```"""

    done, requirements = parse_question_completion(response)

    assert done is True
    assert "Architecture:" in requirements or "architecture" in requirements.lower()
    assert "Application Gateway" in requirements or "application gateway" in requirements.lower()
    assert "private" in requirements.lower()


def test_parse_completion_with_networking_requirements():
    """Should handle networking and gateway requirements in the summary."""
    response = """```json
{
  "requirements": "Workload: API backend; Region: West Europe; Environment: Production; Availability: Zone-redundant; Architecture: Private networking with VNet integration, API Management gateway, private endpoints; Services: Azure Functions Premium, Azure SQL Database, API Management; Scale: 5000 requests/sec peak",
  "done": true
}
```"""

    done, requirements = parse_question_completion(response)

    assert done is True
    assert "Private networking" in requirements or "private networking" in requirements.lower()
    assert "API Management" in requirements or "api management" in requirements.lower()
