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
