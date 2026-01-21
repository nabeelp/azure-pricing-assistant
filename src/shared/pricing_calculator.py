"""Azure Pricing Calculator automation helpers using Playwright MCP.

This module provides functions to automate the Azure Pricing Calculator
at https://azure.microsoft.com/en-us/pricing/calculator/.

The automation uses Playwright MCP's accessibility tree-based approach for
reliable interaction with the calculator.
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Azure Pricing Calculator URL
PRICING_CALCULATOR_URL = "https://azure.microsoft.com/en-us/pricing/calculator/"


class CalculatorWorkflow:
    """
    Workflow instructions for automating the Azure Pricing Calculator.
    
    This class provides documentation and guidance for agents using
    Playwright MCP to interact with the calculator.
    """
    
    @staticmethod
    def get_workflow_instructions() -> str:
        """
        Return detailed workflow instructions for calculator automation.
        
        These instructions are designed to be included in agent prompts
        to guide them through the automation process.
        """
        return """
## Azure Pricing Calculator Automation Workflow

### URL
Navigate to: https://azure.microsoft.com/en-us/pricing/calculator/

### General Workflow
1. **Navigate** to the calculator URL
2. **Search** for the Azure service you want to add
3. **Add** the service to the estimate
4. **Configure** the service with SKU, region, quantity, and other parameters
5. **Extract** pricing data from the calculator
6. **Repeat** for additional services

### Key Selectors and Elements (Use browser_snapshot to discover current selectors)

**Search and Add Services:**
- Search box: Look for input with placeholder text like "Search products and services"
- Service tiles: Look for clickable elements with service names (e.g., "Virtual Machines", "App Service")
- Add button: Usually labeled "Add to estimate" or similar

**Service Configuration:**
- Region dropdown: Look for dropdown labeled "Region" or "Location"
- SKU/Tier selector: Look for dropdown or radio buttons for tier selection (Basic, Standard, Premium, etc.)
- Quantity input: Look for numeric input field labeled "Instances", "Quantity", or similar
- Additional options: Depend on service type (storage size, compute hours, etc.)

**Price Extraction:**
- Monthly estimate: Look for text containing "Estimated monthly cost" or similar
- Service breakdown: Look for table or list showing per-service costs
- Total: Look for element with total cost, usually prominently displayed

### Complex Services (e.g., AKS)

For services with nested resources like AKS:
1. Add the AKS service
2. Configure cluster settings (region, tier)
3. **Important**: Also add and configure node pool resources:
   - Look for "Add node pool" or similar option
   - Configure VM SKU, node count for each pool
4. The calculator will properly account for all resources within the cluster

### Error Handling

- If a service is not found: Try alternate search terms or service names
- If configuration fails: Use browser_snapshot to inspect current page state
- If pricing extraction fails: Log the error and set cost to $0.00 with error note
- Always include service in BOM with error details even if pricing fails

### Best Practices

1. **Use browser_snapshot first** to understand page structure before interaction
2. **Wait after actions** using browser_wait_for to ensure page updates
3. **Verify state** after configuration changes
4. **Batch operations** when possible - add all services before final extraction
5. **Clear calculator** between independent estimates for clean state

### Example Sequence

```
1. browser_navigate(url=CALCULATOR_URL)
2. browser_snapshot() - to see page structure
3. browser_type(element="search box", text="Virtual Machines")
4. browser_click(element="Virtual Machines tile")
5. browser_click(element="Add to estimate button")
6. browser_select_option(element="Region dropdown", value="East US")
7. browser_select_option(element="Tier dropdown", value="Standard_D2s_v3")
8. browser_type(element="Quantity input", text="2")
9. browser_snapshot() - to extract pricing data
10. Repeat for next service...
```
"""
    
    @staticmethod
    def get_service_configuration_hints() -> Dict[str, str]:
        """
        Return service-specific configuration hints.
        
        These provide guidance on how to configure different Azure services
        in the calculator.
        """
        return {
            "Virtual Machines": """
            - Select OS type (Linux/Windows) - Windows includes OS license cost
            - Choose VM size/SKU (e.g., Standard_D2s_v3)
            - Set number of instances
            - Configure managed disks separately if needed
            - Consider availability zones and reserved instances for savings
            """,
            "App Service": """
            - Select tier: Free, Basic (B1, B2, B3), Standard (S1, S2, S3), Premium (P1v2, P1v3, etc.)
            - Windows plans typically cost more than Linux
            - Set number of instances for scale-out scenarios
            - Consider Premium tier for production workloads with auto-scaling
            """,
            "Azure SQL Database": """
            - Choose service tier: Basic, Standard (S0-S12), Premium (P1-P15)
            - Or vCore-based: General Purpose, Business Critical, Hyperscale
            - Set database size (GB)
            - Consider elastic pools for multiple databases
            - Storage costs may be separate for vCore-based tiers
            """,
            "Azure Kubernetes Service": """
            - CRITICAL: AKS control plane is free
            - Configure node pools with VM SKUs (e.g., Standard_DS2_v2)
            - Set node count per pool
            - Add multiple node pools if needed (system pool + user pools)
            - Load balancer and public IP are typically included
            - The calculator properly accounts for nodes as cluster resources
            """,
            "Storage": """
            - Choose redundancy: LRS, ZRS, GRS, RA-GRS
            - Select performance tier: Standard or Premium
            - Set capacity in GB or TB
            - Account for access tier: Hot, Cool, Archive
            - Operations and data transfer may be additional
            """,
            "Azure Functions": """
            - Consumption plan (Y1) has generous free tier
            - Premium plans (EP1, EP2, EP3) for always-on and VNet integration
            - Execution count and duration billed separately in Consumption
            - Premium plans billed per hour like App Service
            """,
            "Azure Cache for Redis": """
            - Select tier: Basic (C0-C6), Standard (C0-C6), Premium (P1-P5)
            - Premium tier supports clustering, persistence, and VNet
            - Pricing varies significantly by tier and size
            - No free tier available
            """,
        }
    
    @staticmethod
    def get_complex_scenario_guidance() -> str:
        """
        Return guidance for handling complex pricing scenarios.
        """
        return """
## Handling Complex Scenarios

### AKS Clusters (Primary Use Case)
The Azure Pricing Calculator properly handles AKS clusters with node pools:

1. **Add AKS Service**: Search for "Kubernetes Service" or "AKS"
2. **Configure Cluster**: 
   - Select region
   - Choose SLA tier (Free or Standard Uptime SLA)
3. **Add Node Pools**:
   - The calculator has UI to add node pools
   - Configure each pool: VM SKU, node count, OS disk size
   - System pool (required): typically 3 nodes
   - User pools (optional): as needed for workloads
4. **Extract Pricing**:
   - Control plane cost (if Standard SLA selected)
   - Each node pool's VM costs
   - Associated load balancer and storage costs

This approach correctly prices nodes as cluster resources, not standalone VMs.

### Multi-Region Deployments
For services in multiple regions:
1. Add each regional instance separately in the calculator
2. Configure with identical settings except region
3. The calculator will show per-region pricing
4. Extract and sum for total cost

### Hybrid Services (VM + Managed Services)
For architectures combining VMs and managed services:
1. Add each component separately
2. Configure networking components (VNet, Load Balancer, Application Gateway)
3. Configure security components (Firewall, WAF)
4. The calculator aggregates all component costs

### Reserved Instances and Savings Plans
The calculator supports savings options:
1. Configure service normally
2. Look for "Pricing options" or "Savings options"
3. Select reserved instance term (1-year, 3-year)
4. Calculator shows both on-demand and reserved pricing
5. Extract both for comparison in proposal
"""


def get_calculator_instructions_for_agent() -> str:
    """
    Return comprehensive instructions for agents using Playwright MCP
    to automate the Azure Pricing Calculator.
    
    This should be included in agent system prompts.
    """
    workflow = CalculatorWorkflow()
    
    instructions = f"""
# Azure Pricing Calculator Automation Guide

{workflow.get_workflow_instructions()}

## Service-Specific Configuration

{chr(10).join(f'**{service}:**{hints}' for service, hints in workflow.get_service_configuration_hints().items())}

{workflow.get_complex_scenario_guidance()}

## Integration with BOM Processing

When processing a Bill of Materials (BOM):

1. **Navigate** to calculator once at the start
2. **Iterate** through BOM items:
   - Add each service
   - Configure with BOM parameters (SKU, region, quantity)
   - No need to extract after each item
3. **Extract pricing** once at the end for all items
4. **Parse** the calculator's output into your pricing JSON format

## Output Format

After extraction, return pricing in this format:
```json
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
      "notes": "Linux VM, Standard SSD"
    }}
  ],
  "total_monthly": 140.16,
  "currency": "USD",
  "pricing_date": "2026-01-21",
  "errors": []
}}
```

## Error Recovery

If calculator interaction fails:
- Log the specific failure point
- Add item to BOM with $0.00 pricing
- Add detailed error to errors array
- Continue with remaining items
- Do not stop the entire process
"""
    
    return instructions
