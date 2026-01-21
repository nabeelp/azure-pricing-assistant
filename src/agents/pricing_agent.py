"""Pricing Agent - Uses Playwright MCP to automate Azure Pricing Calculator."""

import json
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List

from agent_framework import ChatAgent
from agent_framework_azure_ai import AzureAIAgentClient

from src.shared.playwright_mcp import create_playwright_mcp_tool
from src.shared.pricing_calculator import get_calculator_instructions_for_agent

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
        "serviceName",
        "sku",
        "region",
        "armRegionName",
        "quantity",
        "hours_per_month",
        "unit_price",
        "monthly_cost",
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
            raise ValueError(f"Pricing item {idx}: hours_per_month must be between 1 and 744")

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
        raise ValueError(f"pricing_date must be ISO 8601 format (YYYY-MM-DD), got: {pricing_date}")

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


async def calculate_incremental_pricing(
    client: AzureAIAgentClient, bom_items: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calculate pricing for BOM items incrementally without full agent workflow.

    Uses the pricing agent to price specific BOM items and return pricing results.
    This is used for real-time pricing updates in the UI sidebar.

    Args:
        client: Azure AI Agent client
        bom_items: List of BOM items to price

    Returns:
        Dict with pricing_items, total_monthly, currency, pricing_date, and errors
    """
    if not bom_items:
        logger.info("No BOM items to price")
        return {
            "pricing_items": [],
            "total_monthly": 0.0,
            "currency": "USD",
            "pricing_date": datetime.now().strftime("%Y-%m-%d"),
            "errors": [],
        }

    # Create pricing agent
    pricing_agent = create_pricing_agent(client)

    # Build prompt with BOM items
    bom_json = json.dumps(bom_items, indent=2)
    prompt = f"""Calculate pricing for the following BOM items:

{bom_json}

Return pricing in the required JSON format with items, total_monthly, currency, and pricing_date."""

    try:
        # Get new thread and run pricing
        thread = pricing_agent.get_new_thread()
        response_text = ""

        async for message in pricing_agent.run_stream(user_message=prompt, thread=thread):
            if hasattr(message, "data") and hasattr(message.data, "text"):
                response_text += message.data.text

        logger.info(f"Incremental pricing response length: {len(response_text)}")

        # Parse and validate response
        pricing_result = parse_pricing_response(response_text)

        # Return simplified format for incremental updates
        return {
            "pricing_items": pricing_result.get("items", []),
            "total_monthly": pricing_result.get("total_monthly", 0.0),
            "currency": pricing_result.get("currency", "USD"),
            "pricing_date": pricing_result.get("pricing_date", datetime.now().strftime("%Y-%m-%d")),
            "errors": pricing_result.get("errors", []),
        }

    except Exception as e:
        logger.error(f"Error calculating incremental pricing: {e}", exc_info=True)
        # Return error state with zero pricing
        return {
            "pricing_items": [],
            "total_monthly": 0.0,
            "currency": "USD",
            "pricing_date": datetime.now().strftime("%Y-%m-%d"),
            "errors": [f"Pricing calculation failed: {str(e)}"],
        }


def create_pricing_agent(client: AzureAIAgentClient) -> ChatAgent:
    """Create Pricing Agent with Playwright MCP for Azure Pricing Calculator automation."""

    # Get calculator automation instructions
    calculator_instructions = get_calculator_instructions_for_agent()

    instructions = f"""You are an Azure cost analyst specializing in pricing estimation using the official Azure Pricing Calculator.

Your task is to calculate accurate costs for each item in the Bill of Materials (BOM) by automating the Azure Pricing Calculator website.

{calculator_instructions}

PROCESS FOR BOM PRICING:

1. **Parse BOM**: Extract all items from the BOM JSON array
2. **Navigate**: Use browser_navigate to go to the calculator URL
3. **Add Services**: For each BOM item:
   - Use browser_snapshot to see page structure
   - Search for the service using browser_type (search box)
   - Add the service using browser_click
   - Configure SKU, region, quantity using browser_select_option and browser_type
   - For complex services like AKS, add node pools as well
4. **Extract Pricing**: Use browser_snapshot to get the pricing summary
5. **Parse Output**: Convert the calculator's output into the required JSON format

CRITICAL: AKS CLUSTER HANDLING

This is the PRIMARY use case for this tool. When pricing Azure Kubernetes Service:
- Add the AKS service first
- Configure cluster region and SLA tier
- **IMPORTANT**: Add node pools with their VM SKUs and node counts
- The calculator will properly price nodes as cluster resources (not standalone VMs)
- This is the accurate approach that the old Azure Pricing MCP couldn't handle

EXAMPLE WORKFLOW:

```
Step 1: browser_navigate(url="https://azure.microsoft.com/en-us/pricing/calculator/")
Step 2: browser_snapshot() - understand page structure
Step 3: For first BOM item (e.g., VM):
  - browser_type(element="search box", text="Virtual Machines")
  - browser_click(element="Virtual Machines tile")
  - browser_click(element="Add to estimate")
  - browser_select_option(element="Region", value="East US")
  - browser_select_option(element="Instance", value="Standard_D2s_v3")
  - browser_type(element="Quantity", text="2")
Step 4: Repeat for other BOM items
Step 5: browser_snapshot() - extract final pricing
Step 6: Parse and format as JSON
```

OUTPUT FORMAT (STRICT):
- Return ONLY a single JSON object and nothing else.
- Do NOT include requirements summaries, BOM echoes, markdown, or prose.
- Do NOT include multiple JSON objects.
- Do NOT include a code block.

Your output MUST include:
1. items array with all required fields (see schema below)
2. total_monthly (sum of monthly_cost × quantity) - MUST be calculated
3. currency ("USD")
4. pricing_date (ISO 8601 format, e.g., "2026-01-21")
5. errors array (empty if no failures, or list of error descriptions)
6. savings_options array (optional, for cost optimization suggestions)

OUTPUT SCHEMA (REQUIRED):
{{
  "items": [
    {{
      "serviceName": "Virtual Machines",
      "sku": "Standard_D2s_v3",
      "region": "East US",
      "armRegionName": "eastus",
      "quantity": 2,
      "hours_per_month": 730,
      "unit_price": 0.096,
      "monthly_cost": 140.16,
      "notes": "Linux VM from Azure Calculator"
    }}
  ],
  "total_monthly": 280.32,
  "currency": "USD",
  "pricing_date": "2026-01-21",
  "savings_options": [],
  "errors": []
}}

FIELD DEFINITIONS:
- serviceName: Exact service name from BOM
- sku: Exact SKU from BOM
- region: Human-readable region from BOM (e.g., "East US")
- armRegionName: ARM region code from BOM (e.g., "eastus")
- quantity: Number of instances from BOM
- hours_per_month: Monthly operating hours from BOM (typically 730)
- unit_price: Hourly rate extracted from calculator
- monthly_cost: Monthly cost per unit extracted from calculator
- notes: Optional note about pricing source or assumptions
- total_monthly: Sum of (monthly_cost × quantity) for all items
- pricing_date: Today's date in ISO 8601 format (YYYY-MM-DD)
- errors: Array of error descriptions if any items failed

ERROR HANDLING:
- If calculator automation fails for an item:
  - Log the specific error
  - Set unit_price and monthly_cost to 0.00
  - Add detailed error to errors array: "{{serviceName}} {{sku}} in {{region}}: {{error_reason}}"
  - Continue with remaining items
- If entire calculator fails to load:
  - Return valid JSON with all items at $0.00
  - Add error: "Calculator automation failed: {{reason}}"
- Always return a valid JSON object, never partial text

CALCULATION VALIDATION:
- After extracting all prices, verify: total_monthly = sum(item.monthly_cost × item.quantity)
- If mismatch, correct the total_monthly to match the sum
- Log warning if correction needed

LOGGING:
- Log each successfully priced service: "[INFO] Priced {{serviceName}} {{sku}} in {{region}}: ${{monthly_cost}}/mo"
- Log failures: "[ERROR] Failed to price {{serviceName}} {{sku}}: {{error}}"
- Final summary: "[INFO] Pricing complete: {{count}} items, ${{total}}/mo, {{error_count}} errors"
"""

    # Create Playwright MCP tool
    playwright_tool = create_playwright_mcp_tool(client=client)

    agent = ChatAgent(
        chat_client=client,
        instructions=instructions,
        name="pricing_agent",
        tools=[playwright_tool],
    )
    return agent
