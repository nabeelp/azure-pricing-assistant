"""Tests for graceful pricing failure handling with $0.00 fallback."""

import pytest
from src.agents.pricing_agent import parse_pricing_response


class TestPricingFailureFallback:
    """Test graceful fallback to $0.00 when pricing lookup fails."""

    def test_single_service_pricing_unavailable(self):
        """Test that a single service with unavailable pricing gets $0.00."""
        response = """{
  "items": [
    {
      "serviceName": "Virtual Machines",
      "sku": "Standard_D2s_v3",
      "region": "East US",
      "armRegionName": "eastus",
      "quantity": 1,
      "hours_per_month": 730,
      "unit_price": 0.00,
      "monthly_cost": 0.00,
      "notes": "Pricing data unavailable for this SKU"
    }
  ],
  "total_monthly": 0.00,
  "currency": "USD",
  "pricing_date": "2026-01-11",
  "errors": ["Virtual Machines Standard_D2s_v3 in eastus: Pricing temporarily unavailable"]
}"""
        result = parse_pricing_response(response)
        
        assert result["items"][0]["unit_price"] == 0.00
        assert result["items"][0]["monthly_cost"] == 0.00
        assert result["total_monthly"] == 0.00
        assert len(result["errors"]) == 1
        assert "unavailable" in result["errors"][0].lower()

    def test_partial_pricing_failure(self):
        """Test that some services priced successfully while others fail with $0.00."""
        response = """{
  "items": [
    {
      "serviceName": "App Service",
      "sku": "P1v2",
      "region": "East US",
      "armRegionName": "eastus",
      "quantity": 1,
      "hours_per_month": 730,
      "unit_price": 0.10,
      "monthly_cost": 73.00
    },
    {
      "serviceName": "SQL Database",
      "sku": "S1",
      "region": "East US",
      "armRegionName": "eastus",
      "quantity": 1,
      "hours_per_month": 730,
      "unit_price": 0.00,
      "monthly_cost": 0.00,
      "notes": "Pricing lookup failed"
    },
    {
      "serviceName": "Storage Account",
      "sku": "Standard_LRS",
      "region": "East US",
      "armRegionName": "eastus",
      "quantity": 1,
      "hours_per_month": 730,
      "unit_price": 0.02,
      "monthly_cost": 14.60
    }
  ],
  "total_monthly": 87.60,
  "currency": "USD",
  "pricing_date": "2026-01-11",
  "errors": ["SQL Database S1 in eastus: SKU not found in pricing catalog"]
}"""
        result = parse_pricing_response(response)
        
        # Verify successful pricing
        assert result["items"][0]["monthly_cost"] == 73.00
        assert result["items"][2]["monthly_cost"] == 14.60
        
        # Verify failed pricing gets $0.00
        assert result["items"][1]["unit_price"] == 0.00
        assert result["items"][1]["monthly_cost"] == 0.00
        
        # Verify error is recorded
        assert len(result["errors"]) == 1
        assert "SQL Database" in result["errors"][0]
        
        # Verify total excludes failed item (73 + 0 + 14.60)
        assert result["total_monthly"] == 87.60

    def test_multiple_pricing_failures(self):
        """Test handling of multiple pricing failures."""
        response = """{
  "items": [
    {
      "serviceName": "Virtual Machines",
      "sku": "Standard_D2s_v3",
      "region": "West Europe",
      "armRegionName": "westeurope",
      "quantity": 2,
      "hours_per_month": 730,
      "unit_price": 0.00,
      "monthly_cost": 0.00,
      "notes": "Region not supported"
    },
    {
      "serviceName": "SQL Database",
      "sku": "Premium_P1",
      "region": "East US",
      "armRegionName": "eastus",
      "quantity": 1,
      "hours_per_month": 730,
      "unit_price": 0.00,
      "monthly_cost": 0.00,
      "notes": "SKU discontinued"
    },
    {
      "serviceName": "Cosmos DB",
      "sku": "Serverless",
      "region": "East US",
      "armRegionName": "eastus",
      "quantity": 1,
      "hours_per_month": 730,
      "unit_price": 0.00,
      "monthly_cost": 0.00,
      "notes": "Consumption-based pricing not estimated"
    }
  ],
  "total_monthly": 0.00,
  "currency": "USD",
  "pricing_date": "2026-01-11",
  "errors": [
    "Virtual Machines Standard_D2s_v3 in westeurope: Region not supported in pricing API",
    "SQL Database Premium_P1 in eastus: SKU not found",
    "Cosmos DB Serverless in eastus: Consumption-based pricing requires usage data"
  ]
}"""
        result = parse_pricing_response(response)
        
        # All items should have $0.00
        for item in result["items"]:
            assert item["unit_price"] == 0.00
            assert item["monthly_cost"] == 0.00
        
        # Verify total is $0.00
        assert result["total_monthly"] == 0.00
        
        # Verify all errors are recorded
        assert len(result["errors"]) == 3
        assert any("Virtual Machines" in err for err in result["errors"])
        assert any("SQL Database" in err for err in result["errors"])
        assert any("Cosmos DB" in err for err in result["errors"])

    def test_pricing_failure_with_quantity_multiplier(self):
        """Test that $0.00 cost is used even with quantity > 1."""
        response = """{
  "items": [
    {
      "serviceName": "Virtual Machines",
      "sku": "Standard_D2s_v3",
      "region": "East US",
      "armRegionName": "eastus",
      "quantity": 5,
      "hours_per_month": 730,
      "unit_price": 0.00,
      "monthly_cost": 0.00,
      "notes": "Pricing API timeout"
    }
  ],
  "total_monthly": 0.00,
  "currency": "USD",
  "pricing_date": "2026-01-11",
  "errors": ["Virtual Machines Standard_D2s_v3 in eastus: Pricing API timeout after 30s"]
}"""
        result = parse_pricing_response(response)
        
        # Even with quantity=5, cost should be 0.00
        assert result["items"][0]["quantity"] == 5
        assert result["items"][0]["unit_price"] == 0.00
        assert result["items"][0]["monthly_cost"] == 0.00
        assert result["total_monthly"] == 0.00
        assert len(result["errors"]) == 1

    def test_error_messages_are_descriptive(self):
        """Test that error messages include service, SKU, region, and reason."""
        response = """{
  "items": [
    {
      "serviceName": "Azure Kubernetes Service",
      "sku": "Standard",
      "region": "South Central US",
      "armRegionName": "southcentralus",
      "quantity": 1,
      "hours_per_month": 730,
      "unit_price": 0.00,
      "monthly_cost": 0.00
    }
  ],
  "total_monthly": 0.00,
  "currency": "USD",
  "pricing_date": "2026-01-11",
  "errors": ["Azure Kubernetes Service Standard in southcentralus: MCP server connection failed"]
}"""
        result = parse_pricing_response(response)
        
        error_msg = result["errors"][0]
        
        # Error should contain service name
        assert "Azure Kubernetes Service" in error_msg
        
        # Error should contain SKU
        assert "Standard" in error_msg
        
        # Error should contain region
        assert "southcentralus" in error_msg
        
        # Error should contain failure reason
        assert "failed" in error_msg.lower() or "connection" in error_msg.lower()

    def test_notes_field_explains_pricing_unavailability(self):
        """Test that notes field provides context when pricing is $0.00."""
        response = """{
  "items": [
    {
      "serviceName": "Virtual Machines",
      "sku": "Standard_NC6",
      "region": "East US",
      "armRegionName": "eastus",
      "quantity": 1,
      "hours_per_month": 730,
      "unit_price": 0.00,
      "monthly_cost": 0.00,
      "notes": "GPU VM pricing requires capacity reservation - contact Azure sales"
    }
  ],
  "total_monthly": 0.00,
  "currency": "USD",
  "pricing_date": "2026-01-11",
  "errors": ["Virtual Machines Standard_NC6 in eastus: GPU pricing not available via API"]
}"""
        result = parse_pricing_response(response)
        
        item = result["items"][0]
        
        # Notes field should explain why pricing is unavailable
        assert "notes" in item
        assert len(item["notes"]) > 0
        assert item["unit_price"] == 0.00
        assert item["monthly_cost"] == 0.00

    def test_empty_errors_array_when_all_successful(self):
        """Test that errors array is empty when all pricing succeeds."""
        response = """{
  "items": [
    {
      "serviceName": "App Service",
      "sku": "B1",
      "region": "East US",
      "armRegionName": "eastus",
      "quantity": 1,
      "hours_per_month": 730,
      "unit_price": 0.05,
      "monthly_cost": 36.50
    }
  ],
  "total_monthly": 36.50,
  "currency": "USD",
  "pricing_date": "2026-01-11",
  "errors": []
}"""
        result = parse_pricing_response(response)
        
        assert len(result["errors"]) == 0
        assert result["items"][0]["unit_price"] > 0.00
        assert result["total_monthly"] > 0.00


class TestPricingFailureTotalCalculation:
    """Test that total_monthly calculation handles $0.00 items correctly."""

    def test_total_excludes_failed_items(self):
        """Test that total is calculated correctly with some $0.00 items."""
        response = """{
  "items": [
    {
      "serviceName": "App Service",
      "sku": "P1v2",
      "region": "East US",
      "armRegionName": "eastus",
      "quantity": 2,
      "hours_per_month": 730,
      "unit_price": 0.10,
      "monthly_cost": 73.00
    },
    {
      "serviceName": "SQL Database",
      "sku": "S1",
      "region": "East US",
      "armRegionName": "eastus",
      "quantity": 1,
      "hours_per_month": 730,
      "unit_price": 0.00,
      "monthly_cost": 0.00
    },
    {
      "serviceName": "Storage Account",
      "sku": "Standard_LRS",
      "region": "East US",
      "armRegionName": "eastus",
      "quantity": 1,
      "hours_per_month": 730,
      "unit_price": 0.02,
      "monthly_cost": 14.60
    }
  ],
  "total_monthly": 160.60,
  "currency": "USD",
  "pricing_date": "2026-01-11",
  "errors": ["SQL Database S1: pricing unavailable"]
}"""
        result = parse_pricing_response(response)
        
        # Total should be: (73.00 * 2) + (0.00 * 1) + (14.60 * 1) = 160.60
        assert result["total_monthly"] == 160.60
        
        # Verify individual costs
        assert result["items"][0]["monthly_cost"] == 73.00
        assert result["items"][1]["monthly_cost"] == 0.00
        assert result["items"][2]["monthly_cost"] == 14.60

    def test_total_is_zero_when_all_fail(self):
        """Test that total is $0.00 when all items fail pricing lookup."""
        response = """{
  "items": [
    {
      "serviceName": "Service A",
      "sku": "SKU_A",
      "region": "East US",
      "armRegionName": "eastus",
      "quantity": 1,
      "hours_per_month": 730,
      "unit_price": 0.00,
      "monthly_cost": 0.00
    },
    {
      "serviceName": "Service B",
      "sku": "SKU_B",
      "region": "East US",
      "armRegionName": "eastus",
      "quantity": 1,
      "hours_per_month": 730,
      "unit_price": 0.00,
      "monthly_cost": 0.00
    }
  ],
  "total_monthly": 0.00,
  "currency": "USD",
  "pricing_date": "2026-01-11",
  "errors": ["Service A: unavailable", "Service B: unavailable"]
}"""
        result = parse_pricing_response(response)
        
        assert result["total_monthly"] == 0.00
        assert len(result["errors"]) == 2


class TestProposalIntegrationWithPricingErrors:
    """Test that proposals handle pricing errors correctly."""

    def test_proposal_agent_instructions_mention_pricing_unavailability(self):
        """Test that proposal agent instructions address handling unavailable pricing."""
        import inspect
        from src.agents.proposal_agent import create_proposal_agent
        
        # Get the source code of the function
        source = inspect.getsource(create_proposal_agent)
        
        # Verify instructions mention handling $0.00 costs
        assert "$0.00" in source or "0.00" in source
        assert "unavailable" in source.lower() or "not available" in source.lower()

    def test_proposal_agent_instructions_include_contact_sales_note(self):
        """Test that proposal agent instructions suggest contacting sales when pricing unavailable."""
        import inspect
        from src.agents.proposal_agent import create_proposal_agent
        
        # Get the source code of the function
        source = inspect.getsource(create_proposal_agent)
        
        # Verify instructions mention contacting Azure sales
        assert "contact" in source.lower() and "sales" in source.lower()
