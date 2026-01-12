"""Tests for complex Azure service mapping accuracy in BOM generation."""

import pytest
from src.agents.bom_agent import parse_bom_response


class TestVirtualMachineMapping:
    """Test Virtual Machines service mapping."""

    def test_vm_service_name(self):
        """Virtual Machines should use exact service name."""
        bom_json = """```json
[
  {
    "serviceName": "Virtual Machines",
    "sku": "Standard_D2s_v3",
    "quantity": 2,
    "region": "East US",
    "armRegionName": "eastus",
    "hours_per_month": 730
  }
]
```"""
        result = parse_bom_response(bom_json)
        assert len(result) == 1
        assert result[0]["serviceName"] == "Virtual Machines"

    def test_vm_sku_format(self):
        """VM SKUs should follow Standard_{series}{size}_v{gen} format."""
        valid_skus = [
            "Standard_B2s",
            "Standard_D2s_v3",
            "Standard_E4s_v5",
            "Standard_F8s_v2",
        ]
        for sku in valid_skus:
            bom_json = f"""```json
[
  {{
    "serviceName": "Virtual Machines",
    "sku": "{sku}",
    "quantity": 1,
    "region": "East US",
    "armRegionName": "eastus",
    "hours_per_month": 730
  }}
]
```"""
            result = parse_bom_response(bom_json)
            assert result[0]["sku"] == sku


class TestAppServiceMapping:
    """Test App Service mapping."""

    def test_app_service_name(self):
        """App Service should use exact name without Azure prefix."""
        bom_json = """```json
[
  {
    "serviceName": "App Service",
    "sku": "P1v3",
    "quantity": 1,
    "region": "East US",
    "armRegionName": "eastus",
    "hours_per_month": 730
  }
]
```"""
        result = parse_bom_response(bom_json)
        assert result[0]["serviceName"] == "App Service"

    def test_app_service_sku_formats(self):
        """App Service SKUs should be valid tier+number combinations."""
        valid_skus = ["B1", "S1", "S2", "P1v2", "P1v3", "P2v3", "I1v2"]
        for sku in valid_skus:
            bom_json = f"""```json
[
  {{
    "serviceName": "App Service",
    "sku": "{sku}",
    "quantity": 1,
    "region": "West US",
    "armRegionName": "westus",
    "hours_per_month": 730
  }}
]
```"""
            result = parse_bom_response(bom_json)
            assert result[0]["sku"] == sku


class TestSQLDatabaseMapping:
    """Test SQL Database mapping."""

    def test_sql_database_name(self):
        """SQL Database should use exact name."""
        bom_json = """```json
[
  {
    "serviceName": "SQL Database",
    "sku": "S1",
    "quantity": 1,
    "region": "East US",
    "armRegionName": "eastus",
    "hours_per_month": 730
  }
]
```"""
        result = parse_bom_response(bom_json)
        assert result[0]["serviceName"] == "SQL Database"

    def test_sql_database_dtu_skus(self):
        """SQL Database DTU-based SKUs should be valid."""
        dtu_skus = ["S0", "S1", "S2", "P1", "P2", "P4"]
        for sku in dtu_skus:
            bom_json = f"""```json
[
  {{
    "serviceName": "SQL Database",
    "sku": "{sku}",
    "quantity": 1,
    "region": "East US",
    "armRegionName": "eastus",
    "hours_per_month": 730
  }}
]
```"""
            result = parse_bom_response(bom_json)
            assert result[0]["sku"] == sku

    def test_sql_database_vcore_skus(self):
        """SQL Database vCore-based SKUs should be valid."""
        vcore_skus = ["GP_Gen5_2", "GP_Gen5_4", "BC_Gen5_2", "BC_Gen5_4"]
        for sku in vcore_skus:
            bom_json = f"""```json
[
  {{
    "serviceName": "SQL Database",
    "sku": "{sku}",
    "quantity": 1,
    "region": "West Europe",
    "armRegionName": "westeurope",
    "hours_per_month": 730
  }}
]
```"""
            result = parse_bom_response(bom_json)
            assert result[0]["sku"] == sku


class TestStorageMapping:
    """Test Storage service mapping."""

    def test_storage_service_name(self):
        """Storage should use exact name."""
        bom_json = """```json
[
  {
    "serviceName": "Storage",
    "sku": "Standard_LRS",
    "quantity": 100,
    "region": "East US",
    "armRegionName": "eastus",
    "hours_per_month": 730
  }
]
```"""
        result = parse_bom_response(bom_json)
        assert result[0]["serviceName"] == "Storage"

    def test_storage_redundancy_skus(self):
        """Storage SKUs should represent redundancy options."""
        redundancy_skus = [
            "Standard_LRS",
            "Standard_GRS",
            "Standard_ZRS",
            "Premium_LRS",
        ]
        for sku in redundancy_skus:
            bom_json = f"""```json
[
  {{
    "serviceName": "Storage",
    "sku": "{sku}",
    "quantity": 50,
    "region": "Southeast Asia",
    "armRegionName": "southeastasia",
    "hours_per_month": 730
  }}
]
```"""
            result = parse_bom_response(bom_json)
            assert result[0]["sku"] == sku

    def test_storage_quantity_represents_capacity(self):
        """Storage quantity should represent GB capacity."""
        bom_json = """```json
[
  {
    "serviceName": "Storage",
    "sku": "Standard_LRS",
    "quantity": 500,
    "region": "East US",
    "armRegionName": "eastus",
    "hours_per_month": 730
  }
]
```"""
        result = parse_bom_response(bom_json)
        assert result[0]["quantity"] == 500


class TestAzureFunctionsMapping:
    """Test Azure Functions mapping."""

    def test_azure_functions_name(self):
        """Azure Functions should include Azure prefix."""
        bom_json = """```json
[
  {
    "serviceName": "Azure Functions",
    "sku": "Y1",
    "quantity": 1,
    "region": "West US",
    "armRegionName": "westus",
    "hours_per_month": 730
  }
]
```"""
        result = parse_bom_response(bom_json)
        assert result[0]["serviceName"] == "Azure Functions"

    def test_azure_functions_consumption_sku(self):
        """Azure Functions Consumption plan uses Y1 SKU."""
        bom_json = """```json
[
  {
    "serviceName": "Azure Functions",
    "sku": "Y1",
    "quantity": 1,
    "region": "East US",
    "armRegionName": "eastus",
    "hours_per_month": 730
  }
]
```"""
        result = parse_bom_response(bom_json)
        assert result[0]["sku"] == "Y1"

    def test_azure_functions_premium_skus(self):
        """Azure Functions Premium plan SKUs should be valid."""
        premium_skus = ["EP1", "EP2", "EP3"]
        for sku in premium_skus:
            bom_json = f"""```json
[
  {{
    "serviceName": "Azure Functions",
    "sku": "{sku}",
    "quantity": 1,
    "region": "North Europe",
    "armRegionName": "northeurope",
    "hours_per_month": 730
  }}
]
```"""
            result = parse_bom_response(bom_json)
            assert result[0]["sku"] == sku


class TestAzureKubernetesServiceMapping:
    """Test Azure Kubernetes Service mapping."""

    def test_aks_service_name(self):
        """AKS should use exact name."""
        bom_json = """```json
[
  {
    "serviceName": "Azure Kubernetes Service",
    "sku": "Free",
    "quantity": 1,
    "region": "East US",
    "armRegionName": "eastus",
    "hours_per_month": 730
  }
]
```"""
        result = parse_bom_response(bom_json)
        assert result[0]["serviceName"] == "Azure Kubernetes Service"


class TestCosmosDBMapping:
    """Test Azure Cosmos DB mapping."""

    def test_cosmos_db_name(self):
        """Cosmos DB should include Azure prefix."""
        bom_json = """```json
[
  {
    "serviceName": "Azure Cosmos DB",
    "sku": "400RU",
    "quantity": 1,
    "region": "West US",
    "armRegionName": "westus",
    "hours_per_month": 730
  }
]
```"""
        result = parse_bom_response(bom_json)
        assert result[0]["serviceName"] == "Azure Cosmos DB"

    def test_cosmos_db_provisioned_throughput_sku(self):
        """Cosmos DB provisioned throughput SKUs should specify RU/s."""
        throughput_skus = ["400RU", "1000RU", "5000RU"]
        for sku in throughput_skus:
            bom_json = f"""```json
[
  {{
    "serviceName": "Azure Cosmos DB",
    "sku": "{sku}",
    "quantity": 1,
    "region": "Southeast Asia",
    "armRegionName": "southeastasia",
    "hours_per_month": 730
  }}
]
```"""
            result = parse_bom_response(bom_json)
            assert result[0]["sku"] == sku


class TestCacheForRedisMapping:
    """Test Azure Cache for Redis mapping."""

    def test_cache_for_redis_name(self):
        """Cache for Redis should use exact name."""
        bom_json = """```json
[
  {
    "serviceName": "Azure Cache for Redis",
    "sku": "C1",
    "quantity": 1,
    "region": "East US",
    "armRegionName": "eastus",
    "hours_per_month": 730
  }
]
```"""
        result = parse_bom_response(bom_json)
        assert result[0]["serviceName"] == "Azure Cache for Redis"

    def test_cache_for_redis_skus(self):
        """Cache for Redis SKUs should be valid tier+size combinations."""
        valid_skus = ["C0", "C1", "C2", "P1", "P2", "P3"]
        for sku in valid_skus:
            bom_json = f"""```json
[
  {{
    "serviceName": "Azure Cache for Redis",
    "sku": "{sku}",
    "quantity": 1,
    "region": "West Europe",
    "armRegionName": "westeurope",
    "hours_per_month": 730
  }}
]
```"""
            result = parse_bom_response(bom_json)
            assert result[0]["sku"] == sku


class TestMultiServiceBOM:
    """Test BOM with multiple complex services."""

    def test_web_app_with_database_bom(self):
        """Test BOM for web app + database scenario."""
        bom_json = """```json
[
  {
    "serviceName": "App Service",
    "sku": "P1v3",
    "quantity": 2,
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
    "serviceName": "Storage",
    "sku": "Standard_LRS",
    "quantity": 100,
    "region": "East US",
    "armRegionName": "eastus",
    "hours_per_month": 730
  }
]
```"""
        result = parse_bom_response(bom_json)
        assert len(result) == 3
        assert result[0]["serviceName"] == "App Service"
        assert result[1]["serviceName"] == "SQL Database"
        assert result[2]["serviceName"] == "Storage"

    def test_microservices_architecture_bom(self):
        """Test BOM for microservices with AKS."""
        bom_json = """```json
[
  {
    "serviceName": "Azure Kubernetes Service",
    "sku": "Free",
    "quantity": 1,
    "region": "West US",
    "armRegionName": "westus",
    "hours_per_month": 730
  },
  {
    "serviceName": "Virtual Machines",
    "sku": "Standard_D4s_v3",
    "quantity": 3,
    "region": "West US",
    "armRegionName": "westus",
    "hours_per_month": 730
  },
  {
    "serviceName": "Azure Cosmos DB",
    "sku": "1000RU",
    "quantity": 1,
    "region": "West US",
    "armRegionName": "westus",
    "hours_per_month": 730
  },
  {
    "serviceName": "Azure Cache for Redis",
    "sku": "P1",
    "quantity": 1,
    "region": "West US",
    "armRegionName": "westus",
    "hours_per_month": 730
  }
]
```"""
        result = parse_bom_response(bom_json)
        assert len(result) == 4
        assert result[0]["serviceName"] == "Azure Kubernetes Service"
        assert result[1]["serviceName"] == "Virtual Machines"
        assert result[2]["serviceName"] == "Azure Cosmos DB"
        assert result[3]["serviceName"] == "Azure Cache for Redis"


class TestServiceNameConsistency:
    """Test that service names match canonical Azure Retail Prices API names."""

    def test_no_azure_prefix_where_not_needed(self):
        """Services like App Service, SQL Database, Storage should NOT have Azure prefix."""
        services_without_prefix = [
            "App Service",
            "SQL Database",
            "Storage",
            "Virtual Machines",
        ]
        for service in services_without_prefix:
            bom_json = f"""```json
[
  {{
    "serviceName": "{service}",
    "sku": "TestSKU",
    "quantity": 1,
    "region": "East US",
    "armRegionName": "eastus",
    "hours_per_month": 730
  }}
]
```"""
            result = parse_bom_response(bom_json)
            assert result[0]["serviceName"] == service
            assert not result[0]["serviceName"].startswith("Azure ")

    def test_azure_prefix_where_needed(self):
        """Services like Azure Functions, Azure Cosmos DB SHOULD have Azure prefix."""
        services_with_prefix = [
            "Azure Functions",
            "Azure Cosmos DB",
            "Azure Kubernetes Service",
            "Azure Cache for Redis",
        ]
        for service in services_with_prefix:
            bom_json = f"""```json
[
  {{
    "serviceName": "{service}",
    "sku": "TestSKU",
    "quantity": 1,
    "region": "West Europe",
    "armRegionName": "westeurope",
    "hours_per_month": 730
  }}
]
```"""
            result = parse_bom_response(bom_json)
            assert result[0]["serviceName"] == service
            assert result[0]["serviceName"].startswith("Azure ")
