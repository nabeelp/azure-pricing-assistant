"""BOM Agent - Generates Bill of Materials (Phase 2: Enhanced)."""

import json
import logging
import os
from typing import List, Dict, Any
from agent_framework import ChatAgent, MCPStreamableHTTPTool
from agent_framework_azure_ai import AzureAIAgentClient

# Default MCP URL if not set in environment
DEFAULT_PRICING_MCP_URL = "http://localhost:8080/sse"

# Configure logging
logging.basicConfig(level=logging.INFO)
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


def validate_bom_json(bom_data: List[Dict[str, Any]]) -> None:
    """
    Validate BOM JSON structure and required fields.
    
    Args:
        bom_data: Parsed BOM JSON array
        
    Raises:
        ValueError: If validation fails
    """
    if not isinstance(bom_data, list):
        raise ValueError("BOM must be a JSON array")
    
    if len(bom_data) == 0:
        raise ValueError("BOM array cannot be empty")
    
    required_fields = [
        "serviceName", "sku", "quantity", 
        "region", "armRegionName", "hours_per_month"
    ]
    
    for idx, item in enumerate(bom_data):
        if not isinstance(item, dict):
            raise ValueError(f"BOM item {idx} must be an object")
        
        # Check required fields
        missing_fields = [field for field in required_fields if field not in item]
        if missing_fields:
            raise ValueError(
                f"BOM item {idx} missing required fields: {', '.join(missing_fields)}"
            )
        
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
            raise ValueError(
                f"BOM item {idx}: hours_per_month must be between 1 and 744"
            )


def parse_bom_response(response: str) -> List[Dict[str, Any]]:
    """
    Parse and validate BOM agent response.
    
    Args:
        response: Raw agent response text
        
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
        validate_bom_json(bom_data)
        
        logger.info(f"Successfully parsed and validated BOM with {len(bom_data)} items")
        return bom_data
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}")
        raise ValueError(f"Invalid JSON format: {e}")
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise


def create_bom_agent(client: AzureAIAgentClient) -> ChatAgent:
    """
    Create BOM Agent with Phase 2 enhanced instructions.
    
    Uses intelligent prompting, Microsoft Learn MCP tool for service/SKU lookup,
    and Azure Pricing MCP's azure_sku_discovery tool for intelligent SKU matching.
    Returns structured JSON array matching BOM schema.
    """
    instructions = """You are an Azure solutions architect specializing in infrastructure design and Bill of Materials (BOM) creation.

Your task is to analyze the customer requirements provided in the conversation history and create a detailed Bill of Materials (BOM) as a JSON array.

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
   Example: Call with service_hint="Python web app small scale" to get matching services and SKUs
   The tool returns a list of services with their available SKUs, allowing you to select the best match for the workload

DISCOVERY WORKFLOW:
For each requirement, follow this process:
1. Identify the workload type from customer requirements (e.g., "web app", "SQL database", "file storage")
2. Use azure_sku_discovery with a natural language hint describing the workload and scale
3. Review the returned services and SKUs to select the best match
4. Use microsoft_docs_search if you need to validate service names or understand advanced features

REQUIREMENTS TO BOM MAPPING:
- Web applications → Azure App Service (Basic, Standard, or Premium tiers based on scale) OR Virtual Machines
- Databases → Azure SQL Database, Azure Database for MySQL/PostgreSQL, or Azure Cosmos DB
- Object storage → Azure Blob Storage
- File shares → Azure Files
- Message queues → Azure Service Bus or Azure Queue Storage
- Analytics → Azure Synapse Analytics or Azure Data Lake
- Machine Learning → Azure Machine Learning
- Functions/Serverless → Azure Functions
- Containers → Azure Kubernetes Service or Azure Container Instances

SKU SELECTION GUIDANCE:
- Small scale (< 1000 users): Basic, B-series, or Free tier options
- Medium scale (1000-10000 users): Standard, D-series, or S-tier options
- Large scale (> 10000 users): Premium, E-series, or P-tier options
- Always use azure_sku_discovery to find the actual available SKU options for your workload
- Use microsoft_docs_search to verify current SKU availability and get latest tier recommendations

JSON SCHEMA (you MUST follow this exactly):
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

REQUIRED FIELDS:
- serviceName: Exact Azure service name (e.g., "Virtual Machines", "Azure App Service", "SQL Database")
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
  {
    "serviceName": "...",
    "sku": "...",
    "quantity": 1,
    "region": "...",
    "armRegionName": "...",
    "hours_per_month": 730
  }
]

Example for a web app with database:

=== CUSTOMER REQUIREMENTS ===
- Workload: Web application with database backend
- Scale: Medium (1000-5000 users)
- Region: East US
- Specific services: App Service, SQL Database

=== BILL OF MATERIALS ===
[
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
  }
]"""

    microsoft_docs_search = MCPStreamableHTTPTool(
        name="Microsoft Learn",
        description="AI assistant with real-time access to official Microsoft documentation.",
        url="https://learn.microsoft.com/api/mcp",
        chat_client=client
    )
    
    # Get MCP URL from environment variable or use default
    mcp_url = os.getenv("AZURE_PRICING_MCP_URL", DEFAULT_PRICING_MCP_URL)

    azure_pricing_mcp = MCPStreamableHTTPTool(
        name="Azure Pricing",
        description="Azure Pricing MCP server providing real-time pricing data, cost estimates, region recommendations, and SKU discovery for Azure services.",
        url=mcp_url
    )
    
    agent = ChatAgent(
        chat_client=client,
        tools=[microsoft_docs_search, azure_pricing_mcp],
        instructions=instructions,
        name="bom_agent"
    )
    
    return agent
