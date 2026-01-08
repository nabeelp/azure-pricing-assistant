"""Test BOM Agent JSON parsing and validation."""

import pytest
import json
from src.agents.bom_agent import (
    extract_json_from_response,
    validate_bom_json,
    parse_bom_response,
)


class TestJSONExtraction:
    """Test JSON extraction from various response formats."""

    def test_extract_from_markdown_json_block(self):
        """Test extracting JSON from ```json code block."""
        response = """Here's the BOM:
```json
[
  {
    "serviceName": "Azure App Service",
    "sku": "P1v2",
    "quantity": 1,
    "region": "East US",
    "armRegionName": "eastus",
    "hours_per_month": 730
  }
]
```
"""
        result = extract_json_from_response(response)
        assert result.strip().startswith("[")
        assert "Azure App Service" in result

    def test_extract_from_generic_code_block(self):
        """Test extracting JSON from generic ``` code block."""
        response = """```
[
  {
    "serviceName": "SQL Database",
    "sku": "S1",
    "quantity": 1,
    "region": "West US",
    "armRegionName": "westus",
    "hours_per_month": 730
  }
]
```"""
        result = extract_json_from_response(response)
        assert result.strip().startswith("[")
        assert "SQL Database" in result

    def test_extract_raw_json_array(self):
        """Test extracting raw JSON array without code blocks."""
        response = """[
  {
    "serviceName": "Virtual Machines",
    "sku": "Standard_D2s_v3",
    "quantity": 2,
    "region": "East US",
    "armRegionName": "eastus",
    "hours_per_month": 730
  }
]"""
        result = extract_json_from_response(response)
        assert result.strip().startswith("[")
        assert "Virtual Machines" in result

    def test_extract_json_with_surrounding_text(self):
        """Test extracting JSON when surrounded by explanatory text."""
        response = """Based on your requirements, here's the BOM:

[
  {
    "serviceName": "Azure App Service",
    "sku": "P1v2",
    "quantity": 1,
    "region": "East US",
    "armRegionName": "eastus",
    "hours_per_month": 730
  }
]

This configuration should meet your needs."""
        result = extract_json_from_response(response)
        assert result.strip().startswith("[")
        assert "Azure App Service" in result

    def test_extract_fails_when_no_json(self):
        """Test that extraction fails gracefully when no JSON present."""
        response = "I couldn't create a BOM for this request."
        with pytest.raises(ValueError, match="Could not extract JSON"):
            extract_json_from_response(response)


class TestBOMValidation:
    """Test BOM JSON validation."""

    def test_valid_single_item_bom(self):
        """Test validation passes for valid single-item BOM."""
        bom = [
            {
                "serviceName": "Azure App Service",
                "sku": "P1v2",
                "quantity": 1,
                "region": "East US",
                "armRegionName": "eastus",
                "hours_per_month": 730,
            }
        ]
        validate_bom_json(bom)  # Should not raise

    def test_valid_multi_item_bom(self):
        """Test validation passes for valid multi-item BOM."""
        bom = [
            {
                "serviceName": "Azure App Service",
                "sku": "P1v2",
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
        validate_bom_json(bom)  # Should not raise

    def test_reject_non_array(self):
        """Test validation rejects non-array input."""
        bom = {"serviceName": "Azure App Service"}
        with pytest.raises(ValueError, match="must be a JSON array"):
            validate_bom_json(bom)

    def test_reject_empty_array(self):
        """Test validation rejects empty array by default."""
        bom = []
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_bom_json(bom)

    def test_allow_empty_array_when_enabled(self):
        """Test validation allows empty array when allow_empty=True."""
        bom = []
        validate_bom_json(bom, allow_empty=True)  # Should not raise

    def test_reject_missing_servicename(self):
        """Test validation rejects missing serviceName."""
        bom = [
            {
                "sku": "P1v2",
                "quantity": 1,
                "region": "East US",
                "armRegionName": "eastus",
                "hours_per_month": 730,
            }
        ]
        with pytest.raises(ValueError, match="missing required fields.*serviceName"):
            validate_bom_json(bom)

    def test_reject_missing_sku(self):
        """Test validation rejects missing sku."""
        bom = [
            {
                "serviceName": "Azure App Service",
                "quantity": 1,
                "region": "East US",
                "armRegionName": "eastus",
                "hours_per_month": 730,
            }
        ]
        with pytest.raises(ValueError, match="missing required fields.*sku"):
            validate_bom_json(bom)

    def test_reject_missing_quantity(self):
        """Test validation rejects missing quantity."""
        bom = [
            {
                "serviceName": "Azure App Service",
                "sku": "P1v2",
                "region": "East US",
                "armRegionName": "eastus",
                "hours_per_month": 730,
            }
        ]
        with pytest.raises(ValueError, match="missing required fields.*quantity"):
            validate_bom_json(bom)

    def test_reject_missing_region(self):
        """Test validation rejects missing region."""
        bom = [
            {
                "serviceName": "Azure App Service",
                "sku": "P1v2",
                "quantity": 1,
                "armRegionName": "eastus",
                "hours_per_month": 730,
            }
        ]
        with pytest.raises(ValueError, match="missing required fields.*region"):
            validate_bom_json(bom)

    def test_reject_missing_armregionname(self):
        """Test validation rejects missing armRegionName."""
        bom = [
            {
                "serviceName": "Azure App Service",
                "sku": "P1v2",
                "quantity": 1,
                "region": "East US",
                "hours_per_month": 730,
            }
        ]
        with pytest.raises(ValueError, match="missing required fields.*armRegionName"):
            validate_bom_json(bom)

    def test_reject_missing_hours_per_month(self):
        """Test validation rejects missing hours_per_month."""
        bom = [
            {
                "serviceName": "Azure App Service",
                "sku": "P1v2",
                "quantity": 1,
                "region": "East US",
                "armRegionName": "eastus",
            }
        ]
        with pytest.raises(ValueError, match="missing required fields.*hours_per_month"):
            validate_bom_json(bom)

    def test_reject_zero_quantity(self):
        """Test validation rejects zero quantity."""
        bom = [
            {
                "serviceName": "Azure App Service",
                "sku": "P1v2",
                "quantity": 0,
                "region": "East US",
                "armRegionName": "eastus",
                "hours_per_month": 730,
            }
        ]
        with pytest.raises(ValueError, match="quantity must be positive"):
            validate_bom_json(bom)

    def test_reject_negative_quantity(self):
        """Test validation rejects negative quantity."""
        bom = [
            {
                "serviceName": "Azure App Service",
                "sku": "P1v2",
                "quantity": -1,
                "region": "East US",
                "armRegionName": "eastus",
                "hours_per_month": 730,
            }
        ]
        with pytest.raises(ValueError, match="quantity must be positive"):
            validate_bom_json(bom)

    def test_reject_invalid_hours_too_high(self):
        """Test validation rejects hours_per_month > 744."""
        bom = [
            {
                "serviceName": "Azure App Service",
                "sku": "P1v2",
                "quantity": 1,
                "region": "East US",
                "armRegionName": "eastus",
                "hours_per_month": 800,
            }
        ]
        with pytest.raises(ValueError, match="hours_per_month must be between"):
            validate_bom_json(bom)

    def test_reject_invalid_hours_zero(self):
        """Test validation rejects hours_per_month = 0."""
        bom = [
            {
                "serviceName": "Azure App Service",
                "sku": "P1v2",
                "quantity": 1,
                "region": "East US",
                "armRegionName": "eastus",
                "hours_per_month": 0,
            }
        ]
        with pytest.raises(ValueError, match="hours_per_month must be between"):
            validate_bom_json(bom)

    def test_accept_float_quantity(self):
        """Test validation accepts float quantity (e.g., 1.5)."""
        bom = [
            {
                "serviceName": "Azure App Service",
                "sku": "P1v2",
                "quantity": 1.5,
                "region": "East US",
                "armRegionName": "eastus",
                "hours_per_month": 730,
            }
        ]
        validate_bom_json(bom)  # Should not raise


class TestEndToEndParsing:
    """Test end-to-end parsing and validation."""

    def test_parse_valid_response_with_code_block(self):
        """Test parsing valid response with JSON in code block."""
        response = """```json
[
  {
    "serviceName": "Azure App Service",
    "sku": "P1v2",
    "quantity": 1,
    "region": "East US",
    "armRegionName": "eastus",
    "hours_per_month": 730
  }
]
```"""
        result = parse_bom_response(response)
        assert len(result) == 1
        assert result[0]["serviceName"] == "Azure App Service"
        assert result[0]["sku"] == "P1v2"
        assert result[0]["quantity"] == 1

    def test_parse_multi_service_bom(self):
        """Test parsing BOM with multiple services."""
        response = """[
  {
    "serviceName": "Azure App Service",
    "sku": "P1v2",
    "quantity": 1,
    "region": "East US",
    "armRegionName": "eastus",
    "hours_per_month": 730
  },
  {
    "serviceName": "SQL Database",
    "sku": "S1",
    "quantity": 1,
    "region": "East US",
    "armRegionName": "eastus",
    "hours_per_month": 730
  },
  {
    "serviceName": "Azure Blob Storage",
    "sku": "Standard_LRS",
    "quantity": 1,
    "region": "East US",
    "armRegionName": "eastus",
    "hours_per_month": 730
  }
]"""
        result = parse_bom_response(response)
        assert len(result) == 3
        assert result[0]["serviceName"] == "Azure App Service"
        assert result[1]["serviceName"] == "SQL Database"
        assert result[2]["serviceName"] == "Azure Blob Storage"

    def test_parse_fails_on_invalid_json(self):
        """Test parsing fails gracefully on invalid JSON."""
        response = """```json
[
  {
    "serviceName": "Azure App Service",
    "sku": "P1v2",
    missing closing brace
]
```"""
        with pytest.raises(ValueError, match="Invalid JSON format"):
            parse_bom_response(response)

    def test_parse_fails_on_missing_fields(self):
        """Test parsing fails on validation error."""
        response = """[
  {
    "serviceName": "Azure App Service",
    "sku": "P1v2"
  }
]"""
        with pytest.raises(ValueError, match="missing required fields"):
            parse_bom_response(response)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
