"""Tests for Azure service name normalization and mapping."""

import pytest
from src.shared.azure_service_names import normalize_service_name, CANONICAL_SERVICE_NAMES


class TestServiceNameNormalization:
    """Test service name normalization to canonical Azure Retail Prices API names."""

    def test_canonical_name_passthrough(self):
        """Test that canonical names are returned unchanged."""
        assert normalize_service_name("Virtual Machines") == "Virtual Machines"
        assert normalize_service_name("App Service") == "App Service"
        assert normalize_service_name("SQL Database") == "SQL Database"
        assert normalize_service_name("Storage") == "Storage"

    def test_case_insensitive_canonical_match(self):
        """Test that canonical names match case-insensitively."""
        assert normalize_service_name("virtual machines") == "Virtual Machines"
        assert normalize_service_name("VIRTUAL MACHINES") == "Virtual Machines"
        assert normalize_service_name("app service") == "App Service"
        assert normalize_service_name("SQL DATABASE") == "SQL Database"

    def test_common_variations_vm(self):
        """Test common Virtual Machines variations."""
        assert normalize_service_name("vm") == "Virtual Machines"
        assert normalize_service_name("vms") == "Virtual Machines"
        assert normalize_service_name("virtual machine") == "Virtual Machines"
        assert normalize_service_name("azure virtual machines") == "Virtual Machines"
        assert normalize_service_name("compute") == "Virtual Machines"

    def test_common_variations_app_service(self):
        """Test common App Service variations."""
        assert normalize_service_name("web app") == "App Service"
        assert normalize_service_name("web apps") == "App Service"
        assert normalize_service_name("webapp") == "App Service"
        assert normalize_service_name("webapps") == "App Service"
        assert normalize_service_name("azure app service") == "App Service"
        assert normalize_service_name("app services") == "App Service"
        assert normalize_service_name("azure web apps") == "App Service"

    def test_common_variations_sql(self):
        """Test common SQL Database variations."""
        assert normalize_service_name("sql") == "SQL Database"
        assert normalize_service_name("azure sql") == "SQL Database"
        assert normalize_service_name("azure sql database") == "SQL Database"
        assert normalize_service_name("sql db") == "SQL Database"
        assert normalize_service_name("database") == "SQL Database"

    def test_common_variations_storage(self):
        """Test common Storage variations."""
        assert normalize_service_name("blob") == "Storage"
        assert normalize_service_name("blobs") == "Storage"
        assert normalize_service_name("blob storage") == "Storage"
        assert normalize_service_name("azure storage") == "Storage"
        assert normalize_service_name("storage account") == "Storage"
        assert normalize_service_name("storage accounts") == "Storage"
        assert normalize_service_name("object storage") == "Storage"

    def test_common_variations_cosmos_db(self):
        """Test common Cosmos DB variations."""
        assert normalize_service_name("cosmos") == "Azure Cosmos DB"
        assert normalize_service_name("cosmosdb") == "Azure Cosmos DB"
        assert normalize_service_name("document db") == "Azure Cosmos DB"

    def test_common_variations_functions(self):
        """Test common Azure Functions variations."""
        assert normalize_service_name("function") == "Azure Functions"
        assert normalize_service_name("functions") == "Azure Functions"
        assert normalize_service_name("serverless") == "Azure Functions"

    def test_common_variations_kubernetes(self):
        """Test common Kubernetes variations."""
        assert normalize_service_name("aks") == "Azure Kubernetes Service"
        assert normalize_service_name("kubernetes") == "Azure Kubernetes Service"

    def test_common_variations_mysql(self):
        """Test common MySQL variations."""
        assert normalize_service_name("mysql") == "Azure Database for MySQL"
        assert normalize_service_name("azure mysql") == "Azure Database for MySQL"

    def test_common_variations_postgresql(self):
        """Test common PostgreSQL variations."""
        assert normalize_service_name("postgres") == "Azure Database for PostgreSQL"
        assert normalize_service_name("postgresql") == "Azure Database for PostgreSQL"
        assert normalize_service_name("azure postgres") == "Azure Database for PostgreSQL"

    def test_common_variations_redis(self):
        """Test common Redis variations."""
        assert normalize_service_name("redis") == "Azure Cache for Redis"
        assert normalize_service_name("cache") == "Azure Cache for Redis"
        assert normalize_service_name("azure redis") == "Azure Cache for Redis"

    def test_common_variations_api_management(self):
        """Test common API Management variations."""
        assert normalize_service_name("apim") == "API Management"
        assert normalize_service_name("api gateway") == "API Management"

    def test_partial_match_in_longer_string(self):
        """Test partial matches work for longer strings."""
        assert normalize_service_name("Azure Web Apps Premium") == "App Service"
        assert normalize_service_name("Azure SQL Database Standard") == "SQL Database"

    def test_whitespace_trimming(self):
        """Test that whitespace is trimmed."""
        assert normalize_service_name("  Virtual Machines  ") == "Virtual Machines"
        assert normalize_service_name("\tApp Service\n") == "App Service"

    def test_unknown_service_returns_original(self):
        """Test that unknown services return the original name."""
        assert normalize_service_name("Unknown Service") == "Unknown Service"
        assert normalize_service_name("Custom Service Name") == "Custom Service Name"

    def test_empty_string_handling(self):
        """Test empty string handling."""
        assert normalize_service_name("") == ""
        assert normalize_service_name(None) is None


class TestServiceNameHints:
    """Test service name hints generation."""

    def test_get_service_name_hints_returns_string(self):
        """Test that get_service_name_hints returns formatted string."""
        from src.shared.azure_service_names import get_service_name_hints
        
        hints = get_service_name_hints()
        assert isinstance(hints, str)
        assert len(hints) > 0

    def test_hints_include_categories(self):
        """Test that hints include major service categories."""
        from src.shared.azure_service_names import get_service_name_hints
        
        hints = get_service_name_hints()
        assert "Compute:" in hints
        assert "Database:" in hints
        assert "Storage:" in hints
        assert "Networking:" in hints

    def test_hints_include_canonical_names(self):
        """Test that hints include canonical service names."""
        from src.shared.azure_service_names import get_service_name_hints
        
        hints = get_service_name_hints()
        assert "Virtual Machines" in hints
        assert "App Service" in hints
        assert "SQL Database" in hints
        assert "Storage" in hints

    def test_hints_include_examples(self):
        """Test that hints include correct vs incorrect examples."""
        from src.shared.azure_service_names import get_service_name_hints
        
        hints = get_service_name_hints()
        assert "EXAMPLES OF INCORRECT vs CORRECT:" in hints
        assert "✗" in hints  # Incorrect marker
        assert "✓" in hints  # Correct marker


