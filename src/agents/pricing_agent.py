"""Pricing Agent - Uses Azure Pricing MCP via SSE for real-time pricing data."""

import json
import logging
import os
import re
from typing import Any, Dict, List

from agent_framework import ChatAgent, MCPStreamableHTTPTool
from agent_framework_azure_ai import AzureAIAgentClient

# Default MCP URL if not set in environment
DEFAULT_PRICING_MCP_URL = "http://localhost:8080/mcp"

# Configure logging
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
    
    # Try to find JSON object directly
    if "{" in response and "}" in response:
        start = response.find("{")
        end = response.rfind("}") + 1
        return response[start:end].strip()
    
    raise ValueError("Could not extract JSON from response")


def validate_pricing_result(data: Any) -> None:
    """
    Validate pricing result structure and required fields.
    
    Args:
        data: Parsed pricing result data
        
    Raises:
        ValueError: If validation fails
    """
    if not isinstance(data, dict):
        raise ValueError("Pricing result must be a JSON object")
    
    # Check required top-level fields
    if "items" not in data:
        raise ValueError("Pricing result missing required field: items")
    if "total_monthly" not in data:
        raise ValueError("Pricing result missing required field: total_monthly")
    if "currency" not in data:
        raise ValueError("Pricing result missing required field: currency")
    if "pricing_date" not in data:
        raise ValueError("Pricing result missing required field: pricing_date")
    
    # Validate items array
    items = data["items"]
    if not isinstance(items, list):
        raise ValueError("items field must be an array")
    
    if len(items) == 0:
        raise ValueError("items array cannot be empty")
    
    required_item_fields = [
        "serviceName", "sku", "region", "armRegionName", "quantity",
        "hours_per_month", "unit_price", "monthly_cost"
    ]
    
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"Pricing item {idx} must be an object")
        
        # Check required fields
        missing_fields = [field for field in required_item_fields if field not in item]
        if missing_fields:
            raise ValueError(
                f"Pricing item {idx} missing required fields: {', '.join(missing_fields)}"
            )
        
        # Validate field types
        if not isinstance(item["serviceName"], str):
            raise ValueError(f"Pricing item {idx}: serviceName must be a string")
        if not isinstance(item["sku"], str):
            raise ValueError(f"Pricing item {idx}: sku must be a string")
        if not isinstance(item["region"], str):
            raise ValueError(f"Pricing item {idx}: region must be a string")
        if not isinstance(item["armRegionName"], str):
            raise ValueError(f"Pricing item {idx}: armRegionName must be a string")
        if not isinstance(item["quantity"], (int, float)):
            raise ValueError(f"Pricing item {idx}: quantity must be a number")
        if not isinstance(item["hours_per_month"], (int, float)):
            raise ValueError(f"Pricing item {idx}: hours_per_month must be a number")
        if not isinstance(item["unit_price"], (int, float)):
            raise ValueError(f"Pricing item {idx}: unit_price must be a number")
        if not isinstance(item["monthly_cost"], (int, float)):
            raise ValueError(f"Pricing item {idx}: monthly_cost must be a number")
        
        # Validate value ranges
        if item["quantity"] <= 0:
            raise ValueError(f"Pricing item {idx}: quantity must be positive")
        if item["hours_per_month"] <= 0 or item["hours_per_month"] > 744:
            raise ValueError(
                f"Pricing item {idx}: hours_per_month must be between 1 and 744"
            )
    
    # Validate top-level fields
    if not isinstance(data["total_monthly"], (int, float)):
        raise ValueError("total_monthly must be a number")
    
    if not isinstance(data["currency"], str):
        raise ValueError("currency must be a string")
    
    # Validate pricing_date format (ISO 8601: YYYY-MM-DD)
    pricing_date = data["pricing_date"]
    if not isinstance(pricing_date, str):
        raise ValueError("pricing_date must be a string")
    
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", pricing_date):
        raise ValueError(
            f"pricing_date must be ISO 8601 format (YYYY-MM-DD), got: {pricing_date}"
        )
    
    # Validate optional fields
    if "savings_options" in data and data["savings_options"] is not None:
        if not isinstance(data["savings_options"], list):
            raise ValueError("savings_options must be an array")
        for opt_idx, opt in enumerate(data["savings_options"]):
            if not isinstance(opt, dict):
                raise ValueError(f"savings_options[{opt_idx}] must be an object")
            if "description" not in opt or "estimated_monthly_savings" not in opt:
                raise ValueError(
                    f"savings_options[{opt_idx}] missing required fields: "
                    "description, estimated_monthly_savings"
                )
    
    if "errors" in data and data["errors"] is not None:
        if not isinstance(data["errors"], list):
            raise ValueError("errors must be an array")


def parse_pricing_response(response: str) -> Dict[str, Any]:
    """
    Parse and validate Pricing Agent response.
    
    Args:
        response: Raw agent response text
        
    Returns:
        Validated pricing result dict
        
    Raises:
        ValueError: If parsing or validation fails
    """
    try:
        # Extract JSON from response
        json_str = extract_json_from_response(response)
        logger.info(f"Extracted JSON: {json_str[:200]}...")
        
        # Parse JSON
        data = json.loads(json_str)
        
        # Validate structure and fields
        validate_pricing_result(data)
        
        logger.info(f"Successfully parsed and validated pricing with {len(data['items'])} items")
        return data
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}")
        raise ValueError(f"Invalid JSON format: {e}")
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise


def create_pricing_agent(client: AzureAIAgentClient) -> ChatAgent:
    """Create Pricing Agent with Azure Pricing MCP tool via SSE."""
    instructions = """You are an Azure cost analyst specializing in pricing estimation using real-time Azure Retail Prices data via the Azure Pricing MCP server.

Your task is to calculate accurate costs for each item in the Bill of Materials (BOM) using the Azure Pricing tools.

AVAILABLE TOOLS:
You have access to the Azure Pricing MCP server with the following tools:

1. azure_cost_estimate - Estimate costs based on usage patterns (PRIMARY TOOL)
   Parameters: service_name, sku_name, region, hours_per_month (default 730), currency_code (default USD)
   Returns: Detailed pricing with hourly_rate, daily_cost, monthly_cost, yearly_cost, and savings plan options

2. azure_price_search - Search Azure retail prices with filtering
   Parameters: service_name, sku_name, region, currency_code, price_type
   Returns: List of matching price records

3. azure_price_compare - Compare prices across regions or SKUs
   Parameters: service_name (required), sku_name, regions (list), currency_code
   Returns: Price comparison data across specified regions

4. azure_region_recommend - Find cheapest regions for a service/SKU
   Parameters: service_name (required), sku_name (required), currency_code
   Returns: Ranked list of regions with prices and savings percentages

5. azure_discover_skus - List available SKUs for a service
   Parameters: service_name (required), region, currency_code
   Returns: List of available SKUs with pricing

6. azure_sku_discovery - Intelligent SKU discovery with fuzzy matching
   Parameters: service_hint (required)
   Returns: Matched services and their SKUs

7. get_customer_discount - Get customer discount information
   Parameters: customer_id (optional)
   Returns: Applicable discount percentage

PROCESS:
1. Parse the BOM JSON from the previous agent's response
2. For each item in the BOM:
   - Use azure_cost_estimate with: service_name (from serviceName), sku_name (from sku), region (from armRegionName)
   - Extract the monthly_cost from the on_demand_pricing section
   - Multiply by quantity if quantity > 1
3. Sum all monthly costs to get the total

COMPLEX SERVICE PRICING HINTS:

When calling azure_cost_estimate for these services, use these service_name values:

1. **Virtual Machines**: service_name="Virtual Machines", sku_name=exact SKU (e.g., "Standard_D2s_v3")
   - Disk pricing is separate; if BOM includes managed disks, price them as service_name="Storage"

2. **App Service**: service_name="App Service", sku_name=exact SKU (e.g., "P1v3", "S1")
   - Watch for Windows vs Linux pricing differences (Windows may include OS license)

3. **SQL Database**: service_name="SQL Database", sku_name=exact SKU (e.g., "S1", "GP_Gen5_2")
   - DTU-based SKUs: "S0", "S1", "P1", etc.
   - vCore-based SKUs: "GP_Gen5_2", "BC_Gen5_4", etc.
   - Storage may be billed separately for vCore-based

4. **Storage**: service_name="Storage", sku_name=redundancy type (e.g., "Standard_LRS", "Premium_LRS")
   - quantity represents GB of storage capacity
   - Watch for tiered pricing (hot, cool, archive access tiers)

5. **Azure Functions**: service_name="Azure Functions", sku_name=plan type (e.g., "Y1", "EP1")
   - Consumption plan (Y1) has a generous free tier
   - Execution time and memory consumption are billed separately

6. **Azure Kubernetes Service**: service_name="Azure Kubernetes Service"
   - Control plane is free; price only the worker node VMs
   - Load Balancer: service_name="Load Balancer", sku_name="Standard"

7. **Azure Cosmos DB**: service_name="Azure Cosmos DB", sku_name=throughput (e.g., "400RU", "1000RU")
   - Provisioned throughput: RU/s (Request Units per second)
   - Storage billed separately per GB

8. **Azure Cache for Redis**: service_name="Azure Cache for Redis", sku_name=tier+size (e.g., "C1", "P1")

IMPORTANT SERVICE NAME CONSISTENCY:
- Always use the EXACT service name from the BOM (serviceName field)
- Do NOT add or remove "Azure" prefix unless it matches the BOM
- Examples: "App Service" not "Azure App Service", "Virtual Machines" not "VMs"
- If the Pricing API requires different naming, handle that in your tool call parameters

TOOL USAGE EXAMPLES:
For a BOM item with serviceName="Virtual Machines", sku="Standard_D2s_v3", armRegionName="eastus":
- Call azure_cost_estimate with service_name="Virtual Machines", sku_name="Standard_D2s_v3", region="eastus"
- The response includes on_demand_pricing.monthly_cost

ERROR HANDLING:
- Wrap each tool call (especially azure_cost_estimate) in error handling
- On success: Log `[INFO] Priced {serviceName} {sku} in {region}: ${monthly_cost:.2f}/mo`
- On failure: Log `[ERROR] Failed to price {serviceName} {sku} in {region}: {error_reason}`
- For failed items:
  - Set unit_price to 0.00
  - Set monthly_cost to 0.00
  - Add to errors array: "{serviceName} {sku} in {region}: {specific error reason}"
- Continue processing remaining items even if one fails (do not stop)
- Fallback strategies:
  - If exact SKU match fails, try azure_sku_discovery with service name
  - If region lookup fails, note it in errors and use $0.00
  - Always include the item in the BOM with $0.00 and error note

CALCULATION VALIDATION:
- After pricing all items, calculate total: sum(item.monthly_cost × item.quantity)
- If calculated total differs from your computed total by more than $0.01:
  - Log a warning with both values
  - Correct the total_monthly in your output to match the sum calculation

LOGGING GUIDANCE:
- Log each service priced at INFO level with amount
- Log all failures at ERROR level with specific reasons
- Include quantity and region context in logs
- Final log: "[INFO] Pricing complete: {count} items, ${total:.2f}/mo, {error_count} errors"

OUTPUT FORMAT:
Return ONLY a JSON object (no code block needed; agent framework will format).

Your output MUST include:
1. items array with all required fields
2. total_monthly (sum of monthly_cost × quantity) - MUST be calculated
3. currency ("USD")
4. pricing_date (ISO 8601 format, e.g., "2026-01-07")
5. errors array (empty if no failures, or list of error descriptions)
6. savings_options array (optional, for cost optimization suggestions)

OUTPUT SCHEMA (REQUIRED):
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
      "notes": "Optional notes about this item"
    }
  ],
  "total_monthly": 514.56,
  "currency": "USD",
  "pricing_date": "2026-01-07",
  "savings_options": [
    {
      "description": "Consider 1-year savings plan for 15% savings",
      "estimated_monthly_savings": 77.18
    }
  ],
  "errors": []
}

FIELD DEFINITIONS:
- serviceName: Exact service name from BOM (e.g., "Virtual Machines")
- sku: Exact SKU from BOM (e.g., "Standard_D2s_v3")
- region: Human-readable region from BOM (e.g., "East US")
- armRegionName: ARM region code from BOM (e.g., "eastus")
- quantity: Number of instances from BOM
- hours_per_month: Monthly operating hours from BOM (typically 730)
- unit_price: Hourly rate (from on_demand_pricing.hourly_rate)
- monthly_cost: Monthly cost per unit (from on_demand_pricing.monthly_cost)
- notes: Optional note if pricing was estimated, unavailable, or subject to assumptions
- total_monthly: Sum of (monthly_cost × quantity) for all items
- pricing_date: Today's date in ISO 8601 format (YYYY-MM-DD)
- errors: Array of error descriptions if any items failed to price (e.g., ["Virtual Machines: Pricing not available in region"])

CALCULATION EXAMPLE:
If BOM has:
- serviceName: "Virtual Machines", sku: "Standard_D2s_v3", quantity: 2, armRegionName: "eastus"

And azure_cost_estimate returns on_demand_pricing.monthly_cost = 257.28:
- monthly_cost = 257.28
- total = 257.28 × 2 = 514.56

ERROR HANDLING:
- If a tool fails or returns no pricing, set unit_price to 0.00 and add to errors array
- Always include the service in errors with a description of the failure
- Continue processing remaining items even if one fails
- Example: "Virtual Machines Standard_D2s_v3 in eastus: Pricing temporarily unavailable"
"""

    # Get MCP URL from environment variable or use default
    mcp_url = os.getenv("AZURE_PRICING_MCP_URL", DEFAULT_PRICING_MCP_URL)

    azure_pricing_mcp = MCPStreamableHTTPTool(
        name="Azure Pricing",
        description="Azure Pricing MCP server providing real-time pricing data, cost estimates, region recommendations, and SKU discovery for Azure services.",
        url=mcp_url
    )

    agent = ChatAgent(
        chat_client=client,
        instructions=instructions,
        name="pricing_agent",
        tools=[azure_pricing_mcp],
    )
    return agent
