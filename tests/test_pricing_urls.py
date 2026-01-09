"""Tests for Azure pricing URL utilities and proposal pricing links."""

import pytest
from src.shared.azure_pricing_urls import (
    get_pricing_url_for_service,
    format_service_with_pricing_link,
    SERVICE_NAME_TO_PRICING_URL,
)


class TestPricingURLMapping:
    """Test Azure service name to pricing URL mapping."""

    def test_virtual_machines_url(self):
        """Test Virtual Machines pricing URL."""
        url = get_pricing_url_for_service("Virtual Machines")
        assert url == "https://azure.microsoft.com/pricing/details/virtual-machines/"

    def test_app_service_url(self):
        """Test App Service pricing URL."""
        url = get_pricing_url_for_service("App Service")
        assert url == "https://azure.microsoft.com/pricing/details/app-service/"

    def test_sql_database_url(self):
        """Test SQL Database pricing URL."""
        url = get_pricing_url_for_service("SQL Database")
        assert url == "https://azure.microsoft.com/pricing/details/azure-sql-database/"

    def test_azure_sql_database_url(self):
        """Test Azure SQL Database (alternate name) pricing URL."""
        url = get_pricing_url_for_service("Azure SQL Database")
        assert url == "https://azure.microsoft.com/pricing/details/azure-sql-database/"

    def test_storage_accounts_url(self):
        """Test Storage Accounts pricing URL."""
        url = get_pricing_url_for_service("Storage Accounts")
        assert url == "https://azure.microsoft.com/pricing/details/storage/"

    def test_cosmos_db_url(self):
        """Test Cosmos DB pricing URL."""
        url = get_pricing_url_for_service("Cosmos DB")
        assert url == "https://azure.microsoft.com/pricing/details/cosmos-db/"

    def test_azure_functions_url(self):
        """Test Azure Functions pricing URL."""
        url = get_pricing_url_for_service("Azure Functions")
        assert url == "https://azure.microsoft.com/pricing/details/functions/"

    def test_kubernetes_service_url(self):
        """Test Azure Kubernetes Service pricing URL."""
        url = get_pricing_url_for_service("Azure Kubernetes Service")
        assert url == "https://azure.microsoft.com/pricing/details/kubernetes-service/"

    def test_unknown_service_fallback(self):
        """Test fallback to pricing calculator for unknown service."""
        url = get_pricing_url_for_service("Unknown Service")
        assert url == "https://azure.microsoft.com/pricing/calculator/"

    def test_empty_service_name_fallback(self):
        """Test fallback for empty service name."""
        url = get_pricing_url_for_service("")
        assert url == "https://azure.microsoft.com/pricing/calculator/"


class TestPricingLinkFormatting:
    """Test markdown link formatting for service names."""

    def test_format_virtual_machines_link(self):
        """Test formatting Virtual Machines as markdown link."""
        link = format_service_with_pricing_link("Virtual Machines")
        assert link == "[Virtual Machines](https://azure.microsoft.com/pricing/details/virtual-machines/)"

    def test_format_app_service_link(self):
        """Test formatting App Service as markdown link."""
        link = format_service_with_pricing_link("App Service")
        assert link == "[App Service](https://azure.microsoft.com/pricing/details/app-service/)"

    def test_format_sql_database_link(self):
        """Test formatting SQL Database as markdown link."""
        link = format_service_with_pricing_link("SQL Database")
        assert link == "[SQL Database](https://azure.microsoft.com/pricing/details/azure-sql-database/)"

    def test_format_unknown_service_link(self):
        """Test formatting unknown service with fallback URL."""
        link = format_service_with_pricing_link("Unknown Service")
        assert link == "[Unknown Service](https://azure.microsoft.com/pricing/calculator/)"

    def test_markdown_link_structure(self):
        """Test that formatted links follow markdown structure."""
        link = format_service_with_pricing_link("Virtual Machines")
        assert link.startswith("[")
        assert "](" in link
        assert link.endswith(")")


class TestServiceMappingCoverage:
    """Test coverage of common Azure services in mapping."""

    def test_mapping_contains_common_services(self):
        """Test that mapping includes commonly used Azure services."""
        common_services = [
            "Virtual Machines",
            "App Service",
            "SQL Database",
            "Storage Accounts",
            "Azure Functions",
            "Cosmos DB",
            "Azure Kubernetes Service",
            "Application Gateway",
            "Load Balancer",
            "Key Vault",
        ]
        for service in common_services:
            assert service in SERVICE_NAME_TO_PRICING_URL

    def test_mapping_includes_alternate_names(self):
        """Test that mapping includes alternate service names."""
        alternate_names = {
            "SQL Database": "Azure SQL Database",
            "Functions": "Azure Functions",
            "AKS": "Azure Kubernetes Service",
            "Storage Accounts": "Azure Storage",
        }
        for alt_name, canonical_name in alternate_names.items():
            alt_url = SERVICE_NAME_TO_PRICING_URL.get(alt_name)
            canonical_url = SERVICE_NAME_TO_PRICING_URL.get(canonical_name)
            assert alt_url == canonical_url

    def test_all_urls_are_https(self):
        """Test that all pricing URLs use HTTPS."""
        for service_name, url in SERVICE_NAME_TO_PRICING_URL.items():
            assert url.startswith("https://"), f"URL for {service_name} should use HTTPS"

    def test_all_urls_point_to_azure_domain(self):
        """Test that all pricing URLs point to azure.microsoft.com."""
        for service_name, url in SERVICE_NAME_TO_PRICING_URL.items():
            assert "azure.microsoft.com" in url, f"URL for {service_name} should be on azure.microsoft.com"
