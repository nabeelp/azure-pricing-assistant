"""Static catalog of common Azure services and their SKUs.

This module provides a fallback for service discovery when the Azure Pricing MCP
is not available. It contains commonly used Azure services and their typical SKUs.
"""

from typing import Dict, List, Optional

# Common Azure services with their typical SKUs
AZURE_SERVICES_CATALOG: Dict[str, Dict[str, any]] = {
    "Virtual Machines": {
        "description": "Compute instances for running applications",
        "common_skus": [
            "Standard_B1s",
            "Standard_B2s",
            "Standard_D2s_v3",
            "Standard_D4s_v3",
            "Standard_D8s_v3",
            "Standard_E2s_v3",
            "Standard_E4s_v3",
            "Standard_F2s_v2",
            "Standard_F4s_v2",
        ],
        "keywords": ["vm", "virtual machine", "compute", "server", "instance"],
    },
    "App Service": {
        "description": "Managed platform for hosting web apps, APIs, and mobile backends",
        "common_skus": [
            "F1",  # Free
            "B1",
            "B2",
            "B3",  # Basic
            "S1",
            "S2",
            "S3",  # Standard
            "P1v2",
            "P2v2",
            "P3v2",  # Premium v2
            "P1v3",
            "P2v3",
            "P3v3",  # Premium v3
        ],
        "keywords": ["web app", "website", "web hosting", "app service", "web service"],
    },
    "Azure SQL Database": {
        "description": "Managed relational database service",
        "common_skus": [
            "Basic",
            "S0",
            "S1",
            "S2",
            "S3",  # Standard
            "P1",
            "P2",
            "P4",  # Premium
            "GP_Gen5_2",
            "GP_Gen5_4",
            "GP_Gen5_8",  # General Purpose vCore
            "BC_Gen5_2",
            "BC_Gen5_4",  # Business Critical vCore
        ],
        "keywords": ["sql", "database", "sql database", "relational database", "rdbms"],
    },
    "Azure Kubernetes Service": {
        "description": "Managed Kubernetes container orchestration service",
        "common_skus": [
            "Free",  # Control plane tier
            "Standard",  # Control plane tier with SLA
        ],
        "keywords": ["aks", "kubernetes", "k8s", "container orchestration", "cluster"],
        "notes": "AKS control plane is free or paid (Standard SLA). Node pools use VM SKUs.",
    },
    "Storage": {
        "description": "Scalable cloud storage for data",
        "common_skus": [
            "Standard_LRS",  # Locally redundant
            "Standard_GRS",  # Geo-redundant
            "Standard_ZRS",  # Zone-redundant
            "Premium_LRS",  # Premium locally redundant
            "Premium_ZRS",  # Premium zone-redundant
        ],
        "keywords": ["storage", "blob", "file storage", "data storage", "disk"],
    },
    "Azure Functions": {
        "description": "Serverless compute for event-driven applications",
        "common_skus": [
            "Y1",  # Consumption plan
            "EP1",
            "EP2",
            "EP3",  # Premium plan
        ],
        "keywords": ["functions", "serverless", "function app", "lambda"],
    },
    "Azure Cache for Redis": {
        "description": "Managed in-memory cache service",
        "common_skus": [
            "C0",
            "C1",
            "C2",
            "C3",
            "C4",
            "C5",
            "C6",  # Basic/Standard
            "P1",
            "P2",
            "P3",
            "P4",
            "P5",  # Premium
        ],
        "keywords": ["redis", "cache", "in-memory cache", "distributed cache"],
    },
    "Azure Cosmos DB": {
        "description": "Globally distributed, multi-model database service",
        "common_skus": ["Provisioned Throughput", "Serverless", "Autoscale"],
        "keywords": ["cosmos", "cosmosdb", "nosql", "document database", "global database"],
        "notes": "Pricing based on RU/s (Request Units per second) and storage.",
    },
    "Application Gateway": {
        "description": "Web traffic load balancer with WAF capabilities",
        "common_skus": [
            "Standard_Small",
            "Standard_Medium",
            "Standard_Large",
            "WAF_Medium",
            "WAF_Large",
            "Standard_v2",
            "WAF_v2",
        ],
        "keywords": [
            "application gateway",
            "load balancer",
            "waf",
            "web application firewall",
        ],
    },
    "Load Balancer": {
        "description": "Layer 4 load balancer for TCP/UDP traffic",
        "common_skus": ["Basic", "Standard"],
        "keywords": ["load balancer", "lb", "traffic distribution"],
    },
    "Azure Monitor": {
        "description": "Monitoring and diagnostics service",
        "common_skus": ["Pay-as-you-go"],
        "keywords": ["monitoring", "log analytics", "application insights", "diagnostics"],
    },
    "Virtual Network": {
        "description": "Private network in Azure",
        "common_skus": ["Standard"],
        "keywords": ["vnet", "virtual network", "network", "private network", "networking"],
    },
}


def search_services(query: str) -> List[Dict[str, str]]:
    """
    Search for Azure services matching the query.

    Args:
        query: Search query (e.g., "web hosting", "database", "kubernetes")

    Returns:
        List of matching services with name and description
    """
    query_lower = query.lower()
    matches = []

    for service_name, service_info in AZURE_SERVICES_CATALOG.items():
        # Check if query matches service name
        if query_lower in service_name.lower():
            matches.append(
                {
                    "serviceName": service_name,
                    "description": service_info["description"],
                    "match_reason": "name",
                }
            )
            continue

        # Check if query matches any keywords
        keywords = service_info.get("keywords", [])
        if any(query_lower in keyword for keyword in keywords):
            matches.append(
                {
                    "serviceName": service_name,
                    "description": service_info["description"],
                    "match_reason": "keyword",
                }
            )

    return matches


def get_service_skus(service_name: str) -> Optional[List[str]]:
    """
    Get common SKUs for a specific service.

    Args:
        service_name: Name of the Azure service

    Returns:
        List of common SKU names, or None if service not found
    """
    service_info = AZURE_SERVICES_CATALOG.get(service_name)
    if service_info:
        return service_info.get("common_skus", [])
    return None


def get_service_info(service_name: str) -> Optional[Dict[str, any]]:
    """
    Get full information about a service.

    Args:
        service_name: Name of the Azure service

    Returns:
        Service information dict, or None if service not found
    """
    return AZURE_SERVICES_CATALOG.get(service_name)


def list_all_services() -> List[str]:
    """
    Get list of all services in the catalog.

    Returns:
        List of service names
    """
    return list(AZURE_SERVICES_CATALOG.keys())


def get_service_guidance(service_name: str) -> str:
    """
    Get guidance for configuring a specific service.

    Args:
        service_name: Name of the Azure service

    Returns:
        Guidance text for the service
    """
    service_info = AZURE_SERVICES_CATALOG.get(service_name)
    if not service_info:
        return f"No guidance available for {service_name}"

    guidance = f"**{service_name}**\n"
    guidance += f"{service_info['description']}\n\n"

    if "common_skus" in service_info:
        guidance += "Common SKUs:\n"
        for sku in service_info["common_skus"][:5]:  # Show first 5
            guidance += f"  - {sku}\n"
        if len(service_info["common_skus"]) > 5:
            guidance += f"  ... and {len(service_info['common_skus']) - 5} more\n"

    if "notes" in service_info:
        guidance += f"\nNotes: {service_info['notes']}\n"

    return guidance
