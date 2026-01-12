"""BOM Agent - Generates Bill of Materials (Phase 2: Enhanced)."""

import json
import logging
import os
from typing import List, Dict, Any
from agent_framework import ChatAgent, MCPStreamableHTTPTool
from agent_framework_azure_ai import AzureAIAgentClient

# Default MCP URL if not set in environment
DEFAULT_PRICING_MCP_URL = "http://localhost:8080/mcp"

# Get logger (setup handled by application entry point)
logger = logging.getLogger(__name__)


def extract_json_from_response(response: str) -> str:
    """
    Extract JSON from agent response, handling markdown code blocks.

    Args:
        response: Agent response text that may contain JSON in code blocks

    Returns:
        Extracted JSON string

    Raises:
        ValueError: If JSON cannot be extracted
    """
    # Try to extract from markdown code block
    if "```json" in response:
        start = response.find("```json") + 7
        end = response.find("```", start)
        if end != -1:
            return response[start:end].strip()

    # Try to extract from generic code block
    if "```" in response:
        start = response.find("```") + 3
        end = response.find("```", start)
        if end != -1:
            json_str = response[start:end].strip()
            # Remove language identifier if present
            if json_str.startswith("json\n"):
                json_str = json_str[5:]
            return json_str

    # Try to find JSON array directly
    if "[" in response and "]" in response:
        start = response.find("[")
        end = response.rfind("]") + 1
        return response[start:end].strip()

    raise ValueError("Could not extract JSON from response")


def validate_bom_json(bom_data: List[Dict[str, Any]], allow_empty: bool = False) -> None:
    """
    Validate BOM JSON structure and required fields.

    Args:
        bom_data: Parsed BOM JSON array
        allow_empty: If True, allows empty arrays (for incremental mode)

    Raises:
        ValueError: If validation fails
    """
    if not isinstance(bom_data, list):
        raise ValueError("BOM must be a JSON array")

    if len(bom_data) == 0 and not allow_empty:
        raise ValueError("BOM array cannot be empty")

    required_fields = [
        "serviceName",
        "sku",
        "quantity",
        "region",
        "armRegionName",
        "hours_per_month",
    ]

    for idx, item in enumerate(bom_data):
        if not isinstance(item, dict):
            raise ValueError(f"BOM item {idx} must be an object")

        # Check required fields
        missing_fields = [field for field in required_fields if field not in item]
        if missing_fields:
            raise ValueError(f"BOM item {idx} missing required fields: {', '.join(missing_fields)}")

        # Validate field types
        if not isinstance(item["serviceName"], str):
            raise ValueError(f"BOM item {idx}: serviceName must be a string")
        if not isinstance(item["sku"], str):
            raise ValueError(f"BOM item {idx}: sku must be a string")
        if not isinstance(item["quantity"], (int, float)):
            raise ValueError(f"BOM item {idx}: quantity must be a number")
        if not isinstance(item["region"], str):
            raise ValueError(f"BOM item {idx}: region must be a string")
        if not isinstance(item["armRegionName"], str):
            raise ValueError(f"BOM item {idx}: armRegionName must be a string")
        if not isinstance(item["hours_per_month"], (int, float)):
            raise ValueError(f"BOM item {idx}: hours_per_month must be a number")

        # Validate quantity is positive
        if item["quantity"] <= 0:
            raise ValueError(f"BOM item {idx}: quantity must be positive")

        # Validate hours_per_month
        if item["hours_per_month"] <= 0 or item["hours_per_month"] > 744:
            raise ValueError(f"BOM item {idx}: hours_per_month must be between 1 and 744")


def parse_bom_response(response: str, allow_empty: bool = False) -> List[Dict[str, Any]]:
    """
    Parse and validate BOM agent response.

    Args:
        response: Raw agent response text
        allow_empty: If True, allows empty arrays (for incremental mode)

    Returns:
        Validated BOM data as list of dictionaries

    Raises:
        ValueError: If parsing or validation fails
    """
    try:
        # Extract JSON from response
        json_str = extract_json_from_response(response)
        logger.info(f"Extracted JSON: {json_str[:200]}...")

        # Parse JSON
        bom_data = json.loads(json_str)

        # Validate structure and fields
        validate_bom_json(bom_data, allow_empty=allow_empty)

        logger.info(f"Successfully parsed and validated BOM with {len(bom_data)} items")
        return bom_data

    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}")
        raise ValueError(f"Invalid JSON format: {e}")
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise


async def validate_bom_item(
    service_name: str, sku: str, region: str, validation_agent, thread
) -> tuple[bool, str]:
    """
    Validate a single BOM item using the validation agent.

    Args:
        service_name: Azure service name
        sku: SKU identifier
        region: ARM region name
        validation_agent: Agent for validation
        thread: Thread for conversation

    Returns:
        Tuple of (is_valid, reason_or_message)
    """
    query = f"Validate that the Azure service '{service_name}' with SKU '{sku}' exists in region '{region}'. Use azure_sku_discovery tool."

    response_text = ""
    async for update in validation_agent.run_stream(query, thread=thread):
        if update.text:
            response_text += update.text

    # Check if validation passed
    response_lower = response_text.lower()
    if "valid" in response_lower and "invalid" not in response_lower:
        return True, response_text.strip()
    else:
        return False, response_text.strip()


async def validate_bom_against_pricing_catalog(
    bom_items: List[Dict[str, Any]], client: AzureAIAgentClient
) -> Dict[str, Any]:
    """
    Validate BOM items against Azure pricing catalog using azure_sku_discovery.

    Args:
        bom_items: List of BOM items to validate
        client: Azure AI client for MCP tool access

    Returns:
        Dictionary with validation results:
        {
            "valid_items": [...],  # Items that passed validation
            "invalid_items": [...],  # Items that failed validation with reasons
            "warnings": [...]  # Non-critical warnings
        }
    """
    from agent_framework import MCPStreamableHTTPTool, ChatAgent

    mcp_url = os.getenv("AZURE_PRICING_MCP_URL", DEFAULT_PRICING_MCP_URL)
    azure_pricing_mcp = MCPStreamableHTTPTool(
        name="Azure Pricing",
        description="Azure Pricing MCP server for SKU validation.",
        url=mcp_url,
    )

    # Create a temporary agent for validation calls
    validation_instructions = """You are a validation assistant.
Call the azure_sku_discovery tool with the provided service and SKU information to verify it exists in the Azure pricing catalog.
Return only the validation result: "VALID" if the service/SKU combination exists, or "INVALID: <reason>" if not found."""

    validation_agent = ChatAgent(
        chat_client=client,
        tools=[azure_pricing_mcp],
        instructions=validation_instructions,
        name="bom_validator",
    )

    valid_items = []
    invalid_items = []
    warnings = []

    for idx, item in enumerate(bom_items):
        service_name = item["serviceName"]
        sku = item["sku"]
        region = item["armRegionName"]

        logger.info(f"Validating BOM item {idx}: {service_name} / {sku} in {region}")

        try:
            thread = validation_agent.get_new_thread()
            is_valid, response_text = await validate_bom_item(
                service_name, sku, region, validation_agent, thread
            )

            if is_valid:
                valid_items.append(item)
                logger.info(f"✓ BOM item {idx} validated successfully")
            else:
                invalid_items.append(
                    {
                        "item": item,
                        "reason": response_text,
                        "index": idx,
                    }
                )
                logger.warning(f"✗ BOM item {idx} validation failed: {response_text}")

        except Exception as e:
            logger.error(f"Error validating BOM item {idx}: {e}")
            warnings.append(
                f"Could not validate item {idx} ({service_name}/{sku}): {str(e)}"
            )
            # On error, assume valid to not block workflow
            valid_items.append(item)

    return {
        "valid_items": valid_items,
        "invalid_items": invalid_items,
        "warnings": warnings,
    }


def create_bom_agent(client: AzureAIAgentClient) -> ChatAgent:
    """
    Create BOM Agent with Phase 2 enhanced instructions.

    Uses intelligent prompting, Microsoft Learn MCP tool for service/SKU lookup,
    and Azure Pricing MCP's azure_sku_discovery tool for intelligent SKU matching.
    Returns structured JSON array matching BOM schema with canonical Azure service names.
    """
    from src.shared.azure_service_names import get_service_name_hints
    
    service_name_hints = get_service_name_hints()
    
    instructions = f"""You are an Azure solutions architect specializing in infrastructure design and Bill of Materials (BOM) creation.

Your task is to analyze the customer requirements provided in the conversation history and create a detailed Bill of Materials (BOM) as a JSON array.

{service_name_hints}

TOOLS AVAILABLE:

1. microsoft_docs_search - Query official Microsoft/Azure documentation
   Use this tool to:
   - Verify the exact service names and capabilities for Azure services
   - Understand current Azure service capabilities and configurations
   - Confirm region availability for specific services
   Example: If requirements mention "Python web app", search for "Azure App Service Python"

2. azure_sku_discovery - Intelligent SKU discovery with fuzzy matching
   Use this tool to:
   - Find matching Azure services and SKUs based on natural language descriptions
   - Discover available SKUs for workload types (e.g., "web app", "database", "machine learning")
   - Get recommendations on appropriate service tiers based on scale requirements
   - Verify SKU availability in the target region
   - IMPORTANT: The tool returns the CORRECT service name to use in your BOM
   Example: Call with service_hint="Python web app small scale" to get matching services and SKUs
   The tool returns a list of services with their available SKUs, allowing you to select the best match for the workload

DISCOVERY WORKFLOW:
For each requirement, follow this process:
1. Identify the workload type from customer requirements (e.g., "web app", "SQL database", "file storage")
2. Use azure_sku_discovery with a natural language hint describing the workload and scale
3. Review the returned services and SKUs - USE THE EXACT SERVICE NAME from the tool response
4. Use microsoft_docs_search if you need to validate service names or understand advanced features

REQUIREMENTS TO BOM MAPPING:
- Web applications → App Service (Basic, Standard, or Premium tiers based on scale) OR Virtual Machines
- Databases → SQL Database, Azure Cosmos DB, Azure Database for MySQL, Azure Database for PostgreSQL
- Object storage → Storage
- File shares → Azure Files
- Message queues → Service Bus or Storage (Queue Storage)
- Analytics → Azure Synapse Analytics or Azure Data Lake
- Machine Learning → Azure Machine Learning
- Functions/Serverless → Azure Functions
- Containers → Azure Kubernetes Service or Container Instances

SKU SELECTION GUIDANCE:
- Small scale (< 1000 users): Basic, B-series, or Free tier options
- Medium scale (1000-10000 users): Standard, D-series, or S-tier options
- Large scale (> 10000 users): Premium, E-series, or P-tier options
- Always use azure_sku_discovery to find the actual available SKU options for your workload
- Use microsoft_docs_search to verify current SKU availability and get latest tier recommendations

COMPLEX SERVICE MAPPING RULES:

1. **Virtual Machines**:
   - serviceName: "Virtual Machines"
   - SKU format: "Standard_{series}{size}_v{generation}" (e.g., "Standard_D2s_v3", "Standard_B2s")
   - Common series: B (Basic), D (General Purpose), E (Memory Optimized), F (Compute Optimized)
   - Consider managed disk pricing separately if needed (serviceName: "Storage", SKU: "StandardSSD_LRS" or "PremiumSSD_LRS")

2. **App Service**:
   - serviceName: "App Service"
   - SKU format: Tier letter + number (e.g., "B1", "S1", "P1v2", "P1v3")
   - Tiers: F (Free), D (Shared), B (Basic), S (Standard), P (Premium), I (Isolated)
   - Example SKUs: "B1" (Basic), "S1" (Standard), "P1v3" (Premium v3)

3. **SQL Database**:
   - serviceName: "SQL Database"
   - For DTU-based: SKU format is tier letter + number (e.g., "S0", "S1", "P1", "P2")
   - For vCore-based: SKU format includes generation (e.g., "GP_Gen5_2", "BC_Gen5_4")
   - Tiers: Basic (Basic), Standard (S), Premium (P), GeneralPurpose (GP), BusinessCritical (BC), Hyperscale (HS)
   - Example SKUs: "S1" (Standard DTU), "GP_Gen5_2" (General Purpose 2 vCore)

4. **Storage Accounts**:
   - serviceName: "Storage"
   - For Blob Storage: SKU represents redundancy (e.g., "Standard_LRS", "Standard_GRS", "Premium_LRS")
   - Storage types are priced by capacity (GB/month) and operations (transactions)
   - Redundancy options: LRS (Locally Redundant), ZRS (Zone Redundant), GRS (Geo-Redundant), GZRS (Geo-Zone Redundant)
   - Performance tiers: Standard (HDD-based), Premium (SSD-based)
   - Example SKUs: "Standard_LRS" (Standard locally redundant), "Premium_LRS" (Premium locally redundant)
   - Note: Specify capacity in GB as quantity field (e.g., quantity: 100 for 100GB)

5. **Azure Functions**:
   - serviceName: "Azure Functions"
   - Consumption Plan: SKU = "Y1" (pay-per-execution, included in free tier for first 1M executions)
   - Premium Plan: SKU format "EP{size}" (e.g., "EP1", "EP2", "EP3")
   - Dedicated App Service Plan: Use "App Service" with appropriate SKU

6. **Azure Kubernetes Service (AKS)**:
   - serviceName: "Azure Kubernetes Service"
   - Control plane is free; only worker node VMs are charged
   - For worker nodes, use "Virtual Machines" service with appropriate SKU
   - Include Azure Load Balancer if using LoadBalancer services (serviceName: "Load Balancer", SKU: "Standard")

7. **Azure Cosmos DB**:
   - serviceName: "Azure Cosmos DB"
   - SKU typically represents throughput in RU/s (Request Units per second)
   - Provisioned throughput: Specify RU/s as SKU (e.g., "400RU", "1000RU")
   - Serverless: Use SKU "Serverless"
   - Storage is billed separately per GB

8. **Azure Cache for Redis**:
   - serviceName: "Azure Cache for Redis"
   - SKU format: Tier letter + cache size (e.g., "C0", "C1", "P1", "P2")
   - Tiers: C (Basic/Standard), P (Premium), E (Enterprise)
   - Example SKUs: "C1" (Standard 1GB), "P1" (Premium 6GB)

JSON SCHEMA (you MUST follow this exactly):
[
  {{
    "serviceName": "Virtual Machines",
    "sku": "Standard_D2s_v3",
    "quantity": 2,
    "region": "East US",
    "armRegionName": "eastus",
    "hours_per_month": 730
  }}
]

REQUIRED FIELDS:
- serviceName: EXACT Azure service name from the canonical list above (e.g., "Virtual Machines", "App Service", "SQL Database")
  DO NOT add "Azure" prefix unless shown in canonical names (e.g., "Azure Functions", "Azure Cosmos DB")
- sku: Specific SKU identifier (e.g., "Standard_D2s_v3", "P1v2", "S1")
- quantity: Number of instances needed (minimum 1)
- region: Human-readable region (e.g., "East US", "West Europe")
- armRegionName: ARM region code (e.g., "eastus", "westeurope") - must match region
- hours_per_month: Always 730 for full month operation

REGION MAPPING (common examples):
- "East US" → "eastus"
- "East US 2" → "eastus2"
- "West US" → "westus"
- "West Europe" → "westeurope"
- "Southeast Asia" → "southeastasia"

OUTPUT FORMAT:
Your response must include BOTH:
1. A summary of the customer requirements (so the next agent has context)
2. The BOM JSON array

Format your response exactly like this:

=== CUSTOMER REQUIREMENTS ===
[Summarize the key requirements: workload type, scale, region, specific services requested]

=== BILL OF MATERIALS ===
[
  {{
    "serviceName": "...",
    "sku": "...",
    "quantity": 1,
    "region": "...",
    "armRegionName": "...",
    "hours_per_month": 730
  }}
]

Example for a web app with database:

=== CUSTOMER REQUIREMENTS ===
- Workload: Web application with database backend
- Scale: Medium (1000-5000 users)
- Region: East US
- Specific services: App Service, SQL Database

=== BILL OF MATERIALS ===
[
  {{
    "serviceName": "App Service",
    "sku": "P1v2",
    "quantity": 1,
    "region": "East US",
    "armRegionName": "eastus",
    "hours_per_month": 730
  }},
  {{
    "serviceName": "SQL Database",
    "sku": "S1",
    "quantity": 1,
    "region": "East US",
    "armRegionName": "eastus",
    "hours_per_month": 730
  }}
]"""

    microsoft_docs_search = MCPStreamableHTTPTool(
        name="Microsoft Learn",
        description="AI assistant with real-time access to official Microsoft documentation.",
        url="https://learn.microsoft.com/api/mcp",
        chat_client=client,
    )

    # Get MCP URL from environment variable or use default
    mcp_url = os.getenv("AZURE_PRICING_MCP_URL", DEFAULT_PRICING_MCP_URL)

    azure_pricing_mcp = MCPStreamableHTTPTool(
        name="Azure Pricing",
        description="Azure Pricing MCP server providing real-time pricing data, cost estimates, region recommendations, and SKU discovery for Azure services.",
        url=mcp_url,
    )

    agent = ChatAgent(
        chat_client=client,
        tools=[microsoft_docs_search, azure_pricing_mcp],
        instructions=instructions,
        name="bom_agent",
    )

    return agent
