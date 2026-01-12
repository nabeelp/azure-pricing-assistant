"""Azure service name mappings for BOM-to-Pricing consistency.

This module provides canonical Azure service names as they appear in the Azure Retail Prices API
and maps common variations to these canonical names to ensure BOM items can be priced accurately.
"""

# Canonical service names as they appear in Azure Retail Prices API
# These MUST match the serviceName field in the pricing API responses
CANONICAL_SERVICE_NAMES = {
    # Compute services
    "virtual_machines": "Virtual Machines",
    "app_service": "App Service",
    "azure_functions": "Azure Functions",
    "container_instances": "Container Instances",
    "kubernetes_service": "Azure Kubernetes Service",
    "batch": "Azure Batch",
    
    # Database services
    "sql_database": "SQL Database",
    "cosmos_db": "Azure Cosmos DB",
    "database_for_mysql": "Azure Database for MySQL",
    "database_for_postgresql": "Azure Database for PostgreSQL",
    "database_for_mariadb": "Azure Database for MariaDB",
    "redis_cache": "Azure Cache for Redis",
    
    # Storage services (note: some services map to "Storage" in pricing API)
    "storage": "Storage",
    "azure_files": "Azure Files",
    
    # Networking services
    "application_gateway": "Application Gateway",
    "load_balancer": "Load Balancer",
    "vpn_gateway": "VPN Gateway",
    "expressroute": "ExpressRoute",
    "virtual_network": "Virtual Network",
    "cdn": "Azure CDN",
    "traffic_manager": "Azure Traffic Manager",
    "front_door": "Azure Front Door",
    
    # Analytics and Big Data
    "synapse_analytics": "Azure Synapse Analytics",
    "databricks": "Azure Databricks",
    "hdinsight": "HDInsight",
    "data_factory": "Data Factory",
    "stream_analytics": "Stream Analytics",
    
    # AI and Machine Learning
    "machine_learning": "Azure Machine Learning",
    "cognitive_services": "Cognitive Services",
    "openai": "Azure OpenAI",
    
    # Integration services
    "service_bus": "Service Bus",
    "event_hubs": "Event Hubs",
    "event_grid": "Event Grid",
    "api_management": "API Management",
    "logic_apps": "Logic Apps",
    
    # Monitoring and Management
    "monitor": "Azure Monitor",
    "log_analytics": "Log Analytics",
    "application_insights": "Application Insights",
    "automation": "Automation",
    
    # Security and Identity
    "key_vault": "Key Vault",
    "active_directory": "Azure Active Directory",
}

# Service name variations mapping to canonical names
# Maps common user inputs and agent outputs to the correct canonical names
SERVICE_NAME_VARIATIONS = {
    # Virtual Machines variations
    "vm": "Virtual Machines",
    "vms": "Virtual Machines",
    "virtual machine": "Virtual Machines",
    "azure virtual machines": "Virtual Machines",
    "compute": "Virtual Machines",
    
    # App Service variations
    "web app": "App Service",
    "web apps": "App Service",
    "webapp": "App Service",
    "webapps": "App Service",
    "azure app service": "App Service",
    "app services": "App Service",
    "azure web apps": "App Service",
    
    # Azure Functions variations
    "function": "Azure Functions",
    "functions": "Azure Functions",
    "serverless": "Azure Functions",
    
    # Kubernetes variations
    "aks": "Azure Kubernetes Service",
    "kubernetes": "Azure Kubernetes Service",
    
    # SQL Database variations
    "sql": "SQL Database",
    "azure sql": "SQL Database",
    "azure sql database": "SQL Database",
    "sql db": "SQL Database",
    "database": "SQL Database",  # Default database to SQL Database
    
    # Cosmos DB variations
    "cosmosdb": "Azure Cosmos DB",
    "cosmos": "Azure Cosmos DB",
    "document db": "Azure Cosmos DB",
    
    # MySQL variations
    "mysql": "Azure Database for MySQL",
    "azure mysql": "Azure Database for MySQL",
    
    # PostgreSQL variations
    "postgres": "Azure Database for PostgreSQL",
    "postgresql": "Azure Database for PostgreSQL",
    "azure postgres": "Azure Database for PostgreSQL",
    "azure postgresql": "Azure Database for PostgreSQL",
    
    # Redis variations
    "redis": "Azure Cache for Redis",
    "cache": "Azure Cache for Redis",
    "azure redis": "Azure Cache for Redis",
    
    # Storage variations
    "blob": "Storage",
    "blobs": "Storage",
    "blob storage": "Storage",
    "azure storage": "Storage",
    "storage account": "Storage",
    "storage accounts": "Storage",
    "object storage": "Storage",
    
    # API Management variations
    "apim": "API Management",
    "api gateway": "API Management",
    
    # Application Gateway variations
    "app gateway": "Application Gateway",
    "appgw": "Application Gateway",
    
    # Azure CDN variations
    "content delivery network": "Azure CDN",
    "cdn": "Azure CDN",
    
    # Monitoring variations
    "monitoring": "Azure Monitor",
    "logs": "Log Analytics",
    "log": "Log Analytics",
    "insights": "Application Insights",
    "app insights": "Application Insights",
}


def normalize_service_name(service_name: str) -> str:
    """
    Normalize a service name to its canonical Azure Retail Prices API name.
    
    Args:
        service_name: Service name from BOM or user input (e.g., "web app", "Azure App Service", "SQL")
        
    Returns:
        Canonical service name as it appears in Azure Retail Prices API
        
    Examples:
        >>> normalize_service_name("web app")
        'App Service'
        >>> normalize_service_name("Azure SQL Database")
        'SQL Database'
        >>> normalize_service_name("Virtual Machines")
        'Virtual Machines'
    """
    if not service_name:
        return service_name
    
    # First try exact match with canonical names (case-insensitive)
    service_lower = service_name.lower().strip()
    
    # Check if it's already a canonical name
    for canonical in CANONICAL_SERVICE_NAMES.values():
        if service_lower == canonical.lower():
            return canonical
    
    # Check variations mapping
    if service_lower in SERVICE_NAME_VARIATIONS:
        return SERVICE_NAME_VARIATIONS[service_lower]
    
    # Check partial matches in variations (e.g., "Azure Web Apps" contains "web apps")
    for variation, canonical in SERVICE_NAME_VARIATIONS.items():
        if variation in service_lower or service_lower in variation:
            return canonical
    
    # If no match found, return original (may need manual mapping)
    return service_name


def get_service_name_hints() -> str:
    """
    Get service name mapping hints as formatted text for agent instructions.
    
    Returns:
        Formatted string with service name mappings
    """
    hints = ["SERVICE NAME MAPPING GUIDANCE:"]
    hints.append("")
    hints.append("CRITICAL: Use these exact service names in your BOM output:")
    hints.append("")
    
    # Group by category
    categories = {
        "Compute": ["Virtual Machines", "App Service", "Azure Functions", "Azure Kubernetes Service"],
        "Database": ["SQL Database", "Azure Cosmos DB", "Azure Database for MySQL", 
                     "Azure Database for PostgreSQL", "Azure Cache for Redis"],
        "Storage": ["Storage"],  # Includes Blob, Files, Managed Disks
        "Networking": ["Application Gateway", "Load Balancer", "VPN Gateway", "Virtual Network"],
        "AI/ML": ["Azure Machine Learning", "Cognitive Services", "Azure OpenAI"],
    }
    
    for category, services in categories.items():
        hints.append(f"{category}:")
        for service in services:
            # Find common variations
            variations = [var for var, canon in SERVICE_NAME_VARIATIONS.items() if canon == service]
            if variations:
                hints.append(f"  - {service} (variations: {', '.join(variations[:3])})")
            else:
                hints.append(f"  - {service}")
        hints.append("")
    
    hints.append("EXAMPLES OF INCORRECT vs CORRECT:")
    hints.append("  ✗ 'Azure App Service' → ✓ 'App Service'")
    hints.append("  ✗ 'Web Apps' → ✓ 'App Service'")
    hints.append("  ✗ 'Azure SQL' → ✓ 'SQL Database'")
    hints.append("  ✗ 'VMs' → ✓ 'Virtual Machines'")
    hints.append("  ✗ 'Blob Storage' → ✓ 'Storage'")
    hints.append("")
    hints.append("If unsure, use azure_sku_discovery tool to find the correct service name.")
    
    return "\n".join(hints)
