# Phase 2 Architecture - Enhanced Implementation

## Overview
Phase 2 implements intelligent agents with real Azure Retail Prices API integration, JSON parsing, dynamic SKU selection, and professional proposal generation.

## Technology Stack
- **Framework**: Microsoft Agent Framework (`agent-framework-azure-ai`)
- **AI Service**: Azure AI Foundry Agent Service
- **MCP Tools**: Microsoft Learn MCP Server for documentation access
- **Pricing API**: Azure Retail Prices API (https://prices.azure.com/api/retail/prices)
- **Authentication**: Azure CLI credentials
- **Language**: Python 3.10+

## High-Level Flow
```
Question Agent (Interactive Chat with Thread)
           ↓
      "We are DONE!" when sufficient info gathered (max 10 turns)
           ↓
Requirements Summary → Sequential Workflow:
  1. BOM Agent → JSON with appropriate SKUs
  2. Pricing Agent → Real API calls + calculations
  3. Proposal Agent → Professional markdown
           ↓
Client-Ready Proposal
```

## Agent Specifications

### 1. Question Agent (Enhanced Interactive Chat)
**Orchestration**: ChatAgent.run_stream() with thread-based conversation (max 10 turns)

**Intelligence**: Adapts questions based on workload type and user responses

**MCP Tools**: Uses Microsoft Learn MCP documentation tool to access latest Azure service information
- Tool: `microsoft_docs_search` - Search official Microsoft/Azure documentation
- Purpose: Retrieve current Azure service capabilities, recommendations, and best practices
- Usage: Agent queries documentation to:
  - Understand latest Azure service offerings for specific workloads
  - Get current SKU options and configurations
  - Access up-to-date region availability
  - Reference best practices for service selection
- Benefit: Ensures questions and recommendations reflect latest Azure features and guidance

**Question Flow**:
1. Workload type (web, database, analytics, ML, etc.)
2. Scale requirements (users, requests, data volume)
3. Specific Azure services or recommendations
4. Deployment region
5. Special requirements (HA, compliance)

**Minimum Required**: Workload + Service + Region

**Termination**: Outputs "We are DONE!" when sufficient information collected

### 2. BOM Agent (Enhanced Sequential - Stage 1)
**Intelligence**: Maps requirements to appropriate Azure services and SKUs

**MCP Tools**: Uses Microsoft Learn MCP documentation tool for service/SKU verification
- Tool: `microsoft_docs_search` - Search official Microsoft/Azure documentation
- Purpose: Verify exact service names, SKU identifiers, and current tier options
- Usage: Agent queries documentation to:
  - Confirm latest service names (e.g., "Azure App Service" vs legacy names)
  - Validate SKU identifiers and tier options for specific services
  - Check region availability for services and SKUs
  - Get current configuration recommendations for workload types
- Benefit: Ensures BOM uses accurate, current service names and valid SKU identifiers

**Service Mapping**:
- Web apps → Azure App Service or VMs
- Databases → SQL Database, Cosmos DB, MySQL/PostgreSQL
- Storage → Blob Storage, Files
- Analytics → Synapse, Data Lake
- ML → Azure Machine Learning
- Functions → Azure Functions
- Containers → AKS, Container Instances

**SKU Selection Logic**:
- Small scale (< 1K users): Basic, B-series
- Medium scale (1K-10K users): Standard, D-series
- Large scale (> 10K users): Premium, E-series

**Output**: Valid JSON array with schema validation
```json
[
  {
    "serviceName": "Azure App Service",
    "sku": "P1v2",
    "quantity": 1,
    "region": "East US",
    "armRegionName": "eastus",
    "hours_per_month": 730
  }
]
```

### 3. Pricing Agent (Enhanced Sequential - Stage 2)
**Intelligence**: Calls Azure Retail Prices API for each BOM item

**External Tool**: `get_azure_price(service_name, sku_name, region) -> float`

**API Integration**:
- Endpoint: `https://prices.azure.com/api/retail/prices`
- Filter: `$filter=serviceName eq '{service}' and skuName eq '{sku}' and armRegionName eq '{region}'`
- Response: Extract `retailPrice` field

**Calculation**: `monthly_cost = retailPrice × quantity × hours_per_month`

**Error Handling**:
- API failure → Use $0 with explanatory note
- No results → Return 0.0, add warning
- Retry once on timeout

**Output**: JSON with itemized costs and total
```json
{
  "items": [
    {
      "service": "Azure App Service",
      "sku": "P1v2",
      "quantity": 1,
      "hourly_price": 0.20,
      "monthly_cost": 146.00,
      "note": ""
    }
  ],
  "total_monthly": 146.00,
  "currency": "USD"
}
```

### 4. Proposal Agent (Enhanced Sequential - Stage 3)
**Intelligence**: Synthesizes all conversation data into professional document

**Proposal Structure**:
1. **Executive Summary** (2-3 paragraphs)
2. **Solution Architecture** (service list with purposes)
3. **Cost Breakdown** (markdown table)
4. **Total Cost Summary** (monthly + annual)
5. **Next Steps** (deployment recommendations)
6. **Assumptions** (operating hours, region, pricing basis)

**Format**: Professional markdown suitable for client delivery

## Workflow Orchestration

### Handoff Workflow (Same as Phase 1)
```python
from agent_framework import HandoffBuilder

workflow = (
    HandoffBuilder(
        name="azure_requirements_gathering",
        participants=[question_agent]
    )
    .set_coordinator("question_agent")
    .with_termination_condition(
        lambda conv: any("We are DONE!" in msg.text for msg in conv if msg.role.value == "assistant")
    )
    .build()
)
```

### Sequential Workflow (Same as Phase 1)
```python
from agent_framework import SequentialBuilder

workflow = SequentialBuilder().participants([
    bom_agent,
    pricing_agent,
    proposal_agent
]).build()
```

### Event Loop (Same as Phase 1)
Event handling logic remains identical to Phase 1.

## File Structure
```
src/
├── agents/
│   ├── __init__.py
│   ├── question_agent.py    # Enhanced instructions
│   ├── bom_agent.py          # JSON parsing + validation
│   ├── pricing_agent.py      # API integration
│   └── proposal_agent.py     # Professional formatting
├── utils/
│   ├── __init__.py
│   └── pricing_api.py        # get_azure_price function
main.py
requirements.txt
.env
.gitignore
```

## Azure Retail Prices API Integration

### Pricing API Helper (`src/utils/pricing_api.py`)
```python
import requests
from typing import Optional

def get_azure_price(
    service_name: str,
    sku_name: str,
    region: str
) -> float:
    """Get Azure retail price for specific SKU in region."""
    url = "https://prices.azure.com/api/retail/prices"
    
    filter_expr = (
        f"serviceName eq '{service_name}' and "
        f"skuName eq '{sku_name}' and "
        f"armRegionName eq '{region}'"
    )
    
    params = {"$filter": filter_expr}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        items = data.get("Items", [])
        
        if items:
            return items[0].get("retailPrice", 0.0)
        else:
            return 0.0
    except Exception as e:
        print(f"API error: {e}")
        return 0.0
```

### Register Tool with Pricing Agent
```python
from agent_framework import FunctionTool

pricing_tool = FunctionTool(
    name="get_azure_price",
    description="Get Azure retail pricing for a service SKU in a region",
    func=get_azure_price
)

pricing_agent = await client.create_agent(
    name="pricing_agent",
    instructions="...",
    tools=[pricing_tool]
)
```

## Data Flow Example

### User Input
```
"I need to deploy a web application for 10,000 users in East US"
```

### Question Agent Output
```
Requirements:
- Workload: Web application
- Scale: 10,000 users/day
- Service: Azure App Service
- Region: East US

We are DONE!
```

### BOM Agent Output
```json
[
  {
    "serviceName": "Azure App Service",
    "sku": "P1v2",
    "quantity": 1,
    "region": "East US",
    "armRegionName": "eastus",
    "hours_per_month": 730
  }
]
```

### Pricing Agent Process
1. Parse BOM JSON
2. Call `get_azure_price("Azure App Service", "P1v2", "eastus")` → returns 0.20
3. Calculate: 0.20 × 1 × 730 = $146.00

### Pricing Agent Output
```json
{
  "items": [
    {
      "service": "Azure App Service",
      "sku": "P1v2",
      "quantity": 1,
      "hourly_price": 0.20,
      "monthly_cost": 146.00,
      "note": ""
    }
  ],
  "total_monthly": 146.00,
  "currency": "USD"
}
```

### Proposal Agent Output
Professional markdown document with all sections populated.

## Error Handling

### Question Agent
- Insufficient info → Continue asking until minimum requirements met
- User exits → Graceful termination

### BOM Agent
- Invalid JSON → Log error, retry with clarification
- Unknown service → Best-effort mapping with warning

### Pricing Agent
- API timeout → Retry once, fallback to $0
- No results → Use $0, add note about pricing unavailability
- Multiple results → Use first result

### Proposal Agent
- Missing data → Generate partial proposal, note missing sections

## Testing Strategy

### Unit Tests
- `get_azure_price()` with real API calls
- JSON parsing for BOM validation
- Cost calculation accuracy

### Integration Tests
- **Scenario 1**: Simple web app
- **Scenario 2**: Web app + database
- **Scenario 3**: Multi-service solution
- **Edge Cases**: Unknown SKU, invalid region, API failure

### Quality Checks
- BOM JSON schema validation
- Pricing calculation verification
- Proposal completeness review

## Success Criteria
- ✅ Question Agent adapts intelligently to workload type
- ✅ BOM Agent produces valid, appropriate SKU selections
- ✅ Pricing Agent successfully calls Azure Retail Prices API
- ✅ Calculations are mathematically correct
- ✅ Proposal is professional and client-ready
- ✅ Error handling works gracefully
