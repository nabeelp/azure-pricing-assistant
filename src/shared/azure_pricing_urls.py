"""Azure pricing URL mapping utilities for proposal generation."""

from typing import Dict


SERVICE_NAME_TO_PRICING_URL: Dict[str, str] = {
    "Virtual Machines": "https://azure.microsoft.com/pricing/details/virtual-machines/",
    "App Service": "https://azure.microsoft.com/pricing/details/app-service/",
    "Azure SQL Database": "https://azure.microsoft.com/pricing/details/azure-sql-database/",
    "SQL Database": "https://azure.microsoft.com/pricing/details/azure-sql-database/",
    "Storage Accounts": "https://azure.microsoft.com/pricing/details/storage/",
    "Azure Storage": "https://azure.microsoft.com/pricing/details/storage/",
    "Cosmos DB": "https://azure.microsoft.com/pricing/details/cosmos-db/",
    "Azure Cosmos DB": "https://azure.microsoft.com/pricing/details/cosmos-db/",
    "Azure Functions": "https://azure.microsoft.com/pricing/details/functions/",
    "Functions": "https://azure.microsoft.com/pricing/details/functions/",
    "Azure Kubernetes Service": "https://azure.microsoft.com/pricing/details/kubernetes-service/",
    "AKS": "https://azure.microsoft.com/pricing/details/kubernetes-service/",
    "Azure Container Instances": "https://azure.microsoft.com/pricing/details/container-instances/",
    "Container Instances": "https://azure.microsoft.com/pricing/details/container-instances/",
    "Azure Cache for Redis": "https://azure.microsoft.com/pricing/details/cache/",
    "Redis Cache": "https://azure.microsoft.com/pricing/details/cache/",
    "Azure Event Hubs": "https://azure.microsoft.com/pricing/details/event-hubs/",
    "Event Hubs": "https://azure.microsoft.com/pricing/details/event-hubs/",
    "Azure Service Bus": "https://azure.microsoft.com/pricing/details/service-bus/",
    "Service Bus": "https://azure.microsoft.com/pricing/details/service-bus/",
    "Azure Load Balancer": "https://azure.microsoft.com/pricing/details/load-balancer/",
    "Load Balancer": "https://azure.microsoft.com/pricing/details/load-balancer/",
    "Application Gateway": "https://azure.microsoft.com/pricing/details/application-gateway/",
    "Azure Application Gateway": "https://azure.microsoft.com/pricing/details/application-gateway/",
    "Azure Front Door": "https://azure.microsoft.com/pricing/details/frontdoor/",
    "Front Door": "https://azure.microsoft.com/pricing/details/frontdoor/",
    "Azure CDN": "https://azure.microsoft.com/pricing/details/cdn/",
    "CDN": "https://azure.microsoft.com/pricing/details/cdn/",
    "Azure Monitor": "https://azure.microsoft.com/pricing/details/monitor/",
    "Monitor": "https://azure.microsoft.com/pricing/details/monitor/",
    "Log Analytics": "https://azure.microsoft.com/pricing/details/monitor/",
    "Azure Key Vault": "https://azure.microsoft.com/pricing/details/key-vault/",
    "Key Vault": "https://azure.microsoft.com/pricing/details/key-vault/",
    "Azure VPN Gateway": "https://azure.microsoft.com/pricing/details/vpn-gateway/",
    "VPN Gateway": "https://azure.microsoft.com/pricing/details/vpn-gateway/",
    "Azure Virtual Network": "https://azure.microsoft.com/pricing/details/virtual-network/",
    "Virtual Network": "https://azure.microsoft.com/pricing/details/virtual-network/",
    "Azure Blob Storage": "https://azure.microsoft.com/pricing/details/storage/blobs/",
    "Blob Storage": "https://azure.microsoft.com/pricing/details/storage/blobs/",
    "Azure Data Lake Storage": "https://azure.microsoft.com/pricing/details/storage/data-lake/",
    "Data Lake Storage": "https://azure.microsoft.com/pricing/details/storage/data-lake/",
    "Azure Synapse Analytics": "https://azure.microsoft.com/pricing/details/synapse-analytics/",
    "Synapse Analytics": "https://azure.microsoft.com/pricing/details/synapse-analytics/",
    "Azure Databricks": "https://azure.microsoft.com/pricing/details/databricks/",
    "Databricks": "https://azure.microsoft.com/pricing/details/databricks/",
    "Azure Machine Learning": "https://azure.microsoft.com/pricing/details/machine-learning/",
    "Machine Learning": "https://azure.microsoft.com/pricing/details/machine-learning/",
    "Azure Cognitive Services": "https://azure.microsoft.com/pricing/details/cognitive-services/",
    "Cognitive Services": "https://azure.microsoft.com/pricing/details/cognitive-services/",
    "Azure API Management": "https://azure.microsoft.com/pricing/details/api-management/",
    "API Management": "https://azure.microsoft.com/pricing/details/api-management/",
    "Azure Logic Apps": "https://azure.microsoft.com/pricing/details/logic-apps/",
    "Logic Apps": "https://azure.microsoft.com/pricing/details/logic-apps/",
    "Azure DevOps": "https://azure.microsoft.com/pricing/details/devops/azure-devops-services/",
    "DevOps": "https://azure.microsoft.com/pricing/details/devops/azure-devops-services/",
}


def get_pricing_url_for_service(service_name: str) -> str:
    """Get Azure pricing page URL for a service name.
    
    Args:
        service_name: Name of the Azure service (e.g., "Virtual Machines", "App Service")
    
    Returns:
        Azure pricing page URL for the service, or generic pricing URL if not found
    """
    pricing_url = SERVICE_NAME_TO_PRICING_URL.get(service_name)
    if pricing_url:
        return pricing_url
    
    # Fallback to Azure pricing calculator
    return "https://azure.microsoft.com/pricing/calculator/"


def format_service_with_pricing_link(service_name: str) -> str:
    """Format service name as markdown link to its pricing page.
    
    Args:
        service_name: Name of the Azure service
    
    Returns:
        Markdown formatted link: [Service Name](pricing_url)
    """
    pricing_url = get_pricing_url_for_service(service_name)
    return f"[{service_name}]({pricing_url})"
