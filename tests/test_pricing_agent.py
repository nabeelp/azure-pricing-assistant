"""Tests for Pricing Agent schema validation and parsing."""

import json
import pytest
from src.agents.pricing_agent import (
    extract_json_from_response,
    validate_pricing_result,
    parse_pricing_response,
)


class TestJSONExtraction:
    """Test JSON extraction from various response formats."""
    
    def test_extract_from_markdown_json_block(self):
        """Test extracting JSON from ```json code block."""
        response = """Here's the pricing:
```json
{
  "items": [
    {
      "serviceName": "Virtual Machines",
      "sku": "Standard_D2s_v3",
      "region": "East US",
      "armRegionName": "eastus",
      "quantity": 1,
      "hours_per_month": 730,
      "unit_price": 0.176,
      "monthly_cost": 128.64,
      "notes": ""
    }
  ],
  "total_monthly": 128.64,
  "currency": "USD",
  "pricing_date": "2026-01-07",
  "errors": []
}
```
"""
        result = extract_json_from_response(response)
        assert result.strip().startswith("{")
        assert "Virtual Machines" in result
        assert "pricing_date" in result
    
    def test_extract_raw_json_object(self):
        """Test extracting raw JSON object without code blocks."""
        response = """{
  "items": [{
    "serviceName": "SQL Database",
    "sku": "S1",
    "region": "West US",
    "armRegionName": "westus",
    "quantity": 1,
    "hours_per_month": 730,
    "unit_price": 0.03,
    "monthly_cost": 21.9,
    "notes": ""
  }],
  "total_monthly": 21.9,
  "currency": "USD",
  "pricing_date": "2026-01-07",
  "errors": []
}"""
        result = extract_json_from_response(response)
        assert result.strip().startswith("{")
        assert "SQL Database" in result
    
    def test_extract_fails_when_no_json(self):
        """Test that extraction fails when no JSON present."""
        response = "Pricing information could not be retrieved."
        with pytest.raises(ValueError, match="Could not extract JSON"):
            extract_json_from_response(response)


class TestPricingValidation:
    """Test pricing result validation."""
    
    def test_valid_single_item_pricing(self):
        """Test validation passes for valid single-item pricing."""
        data = {
            "items": [
                {
                    "serviceName": "Virtual Machines",
                    "sku": "Standard_D2s_v3",
                    "region": "East US",
                    "armRegionName": "eastus",
                    "quantity": 1,
                    "hours_per_month": 730,
                    "unit_price": 0.176,
                    "monthly_cost": 128.64,
                    "notes": ""
                }
            ],
            "total_monthly": 128.64,
            "currency": "USD",
            "pricing_date": "2026-01-07",
            "errors": []
        }
        validate_pricing_result(data)  # Should not raise
    
    def test_valid_multi_item_pricing(self):
        """Test validation passes for multiple items."""
        data = {
            "items": [
                {
                    "serviceName": "Virtual Machines",
                    "sku": "Standard_D2s_v3",
                    "region": "East US",
                    "armRegionName": "eastus",
                    "quantity": 2,
                    "hours_per_month": 730,
                    "unit_price": 0.176,
                    "monthly_cost": 257.28,
                    "notes": ""
                },
                {
                    "serviceName": "SQL Database",
                    "sku": "S1",
                    "region": "East US",
                    "armRegionName": "eastus",
                    "quantity": 1,
                    "hours_per_month": 730,
                    "unit_price": 0.03,
                    "monthly_cost": 21.9,
                    "notes": ""
                }
            ],
            "total_monthly": 279.18,
            "currency": "USD",
            "pricing_date": "2026-01-07",
            "savings_options": [
                {
                    "description": "1-year savings plan",
                    "estimated_monthly_savings": 42.0
                }
            ],
            "errors": []
        }
        validate_pricing_result(data)  # Should not raise
    
    def test_reject_missing_servicename(self):
        """Test validation rejects missing serviceName."""
        data = {
            "items": [{
                "sku": "Standard_D2s_v3",
                "region": "East US",
                "armRegionName": "eastus",
                "quantity": 1,
                "hours_per_month": 730,
                "unit_price": 0.176,
                "monthly_cost": 128.64
            }],
            "total_monthly": 128.64,
            "currency": "USD",
            "pricing_date": "2026-01-07",
            "errors": []
        }
        with pytest.raises(ValueError, match="serviceName"):
            validate_pricing_result(data)
    
    def test_reject_missing_pricing_date(self):
        """Test validation rejects missing pricing_date."""
        data = {
            "items": [{
                "serviceName": "Virtual Machines",
                "sku": "Standard_D2s_v3",
                "region": "East US",
                "armRegionName": "eastus",
                "quantity": 1,
                "hours_per_month": 730,
                "unit_price": 0.176,
                "monthly_cost": 128.64
            }],
            "total_monthly": 128.64,
            "currency": "USD",
            "errors": []
        }
        with pytest.raises(ValueError, match="pricing_date"):
            validate_pricing_result(data)
    
    def test_reject_invalid_pricing_date_format(self):
        """Test validation rejects non-ISO 8601 date format."""
        data = {
            "items": [{
                "serviceName": "Virtual Machines",
                "sku": "Standard_D2s_v3",
                "region": "East US",
                "armRegionName": "eastus",
                "quantity": 1,
                "hours_per_month": 730,
                "unit_price": 0.176,
                "monthly_cost": 128.64
            }],
            "total_monthly": 128.64,
            "currency": "USD",
            "pricing_date": "01/07/2026",  # Invalid format
            "errors": []
        }
        with pytest.raises(ValueError, match="ISO 8601"):
            validate_pricing_result(data)
    
    def test_reject_invalid_hours_per_month(self):
        """Test validation rejects hours_per_month outside 1-744 range."""
        data = {
            "items": [{
                "serviceName": "Virtual Machines",
                "sku": "Standard_D2s_v3",
                "region": "East US",
                "armRegionName": "eastus",
                "quantity": 1,
                "hours_per_month": 800,  # Invalid: > 744
                "unit_price": 0.176,
                "monthly_cost": 128.64
            }],
            "total_monthly": 128.64,
            "currency": "USD",
            "pricing_date": "2026-01-07",
            "errors": []
        }
        with pytest.raises(ValueError, match="hours_per_month"):
            validate_pricing_result(data)
    
    def test_reject_zero_quantity(self):
        """Test validation rejects zero quantity."""
        data = {
            "items": [{
                "serviceName": "Virtual Machines",
                "sku": "Standard_D2s_v3",
                "region": "East US",
                "armRegionName": "eastus",
                "quantity": 0,
                "hours_per_month": 730,
                "unit_price": 0.176,
                "monthly_cost": 128.64
            }],
            "total_monthly": 128.64,
            "currency": "USD",
            "pricing_date": "2026-01-07",
            "errors": []
        }
        with pytest.raises(ValueError, match="quantity"):
            validate_pricing_result(data)
    
    def test_reject_non_array_items(self):
        """Test validation rejects non-array items field."""
        data = {
            "items": {
                "serviceName": "Virtual Machines",
                "sku": "Standard_D2s_v3"
            },
            "total_monthly": 128.64,
            "currency": "USD",
            "pricing_date": "2026-01-07",
            "errors": []
        }
        with pytest.raises(ValueError, match="array"):
            validate_pricing_result(data)
    
    def test_accept_optional_savings_options(self):
        """Test validation accepts optional savings_options array."""
        data = {
            "items": [{
                "serviceName": "Virtual Machines",
                "sku": "Standard_D2s_v3",
                "region": "East US",
                "armRegionName": "eastus",
                "quantity": 1,
                "hours_per_month": 730,
                "unit_price": 0.176,
                "monthly_cost": 128.64
            }],
            "total_monthly": 128.64,
            "currency": "USD",
            "pricing_date": "2026-01-07",
            "savings_options": [
                {
                    "description": "1-year savings plan",
                    "estimated_monthly_savings": 19.30
                }
            ],
            "errors": []
        }
        validate_pricing_result(data)  # Should not raise
    
    def test_accept_optional_errors(self):
        """Test validation accepts optional errors array."""
        data = {
            "items": [{
                "serviceName": "Virtual Machines",
                "sku": "Standard_D2s_v3",
                "region": "East US",
                "armRegionName": "eastus",
                "quantity": 1,
                "hours_per_month": 730,
                "unit_price": 0.0,
                "monthly_cost": 0.0,
                "notes": "Pricing failed"
            }],
            "total_monthly": 0.0,
            "currency": "USD",
            "pricing_date": "2026-01-07",
            "errors": ["Virtual Machines in eastus: pricing unavailable"]
        }
        validate_pricing_result(data)  # Should not raise


class TestEndToEndParsing:
    """Test end-to-end parsing and validation."""
    
    def test_parse_valid_response_with_code_block(self):
        """Test parsing valid response with JSON in code block."""
        response = """```json
{
  "items": [
    {
      "serviceName": "Virtual Machines",
      "sku": "Standard_D2s_v3",
      "region": "East US",
      "armRegionName": "eastus",
      "quantity": 2,
      "hours_per_month": 730,
      "unit_price": 0.176,
      "monthly_cost": 257.28,
      "notes": ""
    }
  ],
  "total_monthly": 514.56,
  "currency": "USD",
  "pricing_date": "2026-01-07",
  "errors": []
}
```"""
        result = parse_pricing_response(response)
        assert len(result["items"]) == 1
        assert result["items"][0]["serviceName"] == "Virtual Machines"
        assert result["total_monthly"] == 514.56
        assert result["pricing_date"] == "2026-01-07"
    
    def test_parse_multi_service_pricing(self):
        """Test parsing pricing with multiple services."""
        response = """{
  "items": [
    {
      "serviceName": "Virtual Machines",
      "sku": "Standard_D2s_v3",
      "region": "East US",
      "armRegionName": "eastus",
      "quantity": 1,
      "hours_per_month": 730,
      "unit_price": 0.176,
      "monthly_cost": 128.64,
      "notes": ""
    },
    {
      "serviceName": "SQL Database",
      "sku": "S1",
      "region": "East US",
      "armRegionName": "eastus",
      "quantity": 1,
      "hours_per_month": 730,
      "unit_price": 0.03,
      "monthly_cost": 21.9,
      "notes": ""
    }
  ],
  "total_monthly": 150.54,
  "currency": "USD",
  "pricing_date": "2026-01-07",
  "errors": []
}"""
        result = parse_pricing_response(response)
        assert len(result["items"]) == 2
        assert result["items"][0]["serviceName"] == "Virtual Machines"
        assert result["items"][1]["serviceName"] == "SQL Database"
        assert result["total_monthly"] == 150.54
    
    def test_parse_with_errors_array(self):
        """Test parsing pricing with errors."""
        response = """{
  "items": [
    {
      "serviceName": "Virtual Machines",
      "sku": "Standard_D2s_v3",
      "region": "East US",
      "armRegionName": "eastus",
      "quantity": 1,
      "hours_per_month": 730,
      "unit_price": 0.0,
      "monthly_cost": 0.0,
      "notes": "Pricing unavailable"
    }
  ],
  "total_monthly": 0.0,
  "currency": "USD",
  "pricing_date": "2026-01-07",
  "errors": ["Virtual Machines in eastus: pricing data not found"]
}"""
        result = parse_pricing_response(response)
        assert len(result["errors"]) == 1
        assert "pricing data not found" in result["errors"][0]
    
    def test_parse_fails_on_invalid_json(self):
        """Test parsing fails gracefully on invalid JSON."""
        response = """```json
{
  "items": [...],
  invalid json here
}
```"""
        with pytest.raises(ValueError, match="Invalid JSON"):
            parse_pricing_response(response)
    
    def test_parse_fails_on_missing_fields(self):
        """Test parsing fails on validation error."""
        response = """{
  "items": [
    {
      "serviceName": "Virtual Machines",
      "sku": "Standard_D2s_v3"
    }
  ],
  "total_monthly": 128.64,
  "currency": "USD",
  "pricing_date": "2026-01-07"
}"""
        with pytest.raises(ValueError, match="region"):
            parse_pricing_response(response)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
