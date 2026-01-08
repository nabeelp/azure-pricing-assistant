# Product Requirements Definition (PRD): Azure Pricing Assistant

## 1. Overview
The **Azure Pricing Assistant** is an AI-powered tool designed to automate the process of gathering customer requirements, designing Azure solutions, estimating costs, and generating professional proposals. It leverages a multi-agent architecture to handle distinct stages of the sales engineering workflow, ensuring accuracy and consistency.

## 2. Goals & Objectives
- **Automate Requirement Gathering**: Replace manual questionnaires with an intelligent, interactive chat interface.
- **Accurate Solution Design**: Automatically map high-level requirements to specific Azure services and SKUs.
- **Real-Time Pricing**: Provide accurate cost estimates using live data from the Azure Retail Prices API.
- **Professional Output**: Generate client-ready proposals in Markdown format without manual formatting.
- **Up-to-Date Knowledge**: Utilize Microsoft Learn documentation to ensure recommendations reflect the latest Azure capabilities.

## 3. User Workflow
1.  **Discovery with Incremental BOM Building**: The user initiates a chat session. The **Question Agent** asks adaptive questions to understand the workload, scale, preferred services, and region. **Simultaneously**, the **BOM Agent** is invoked incrementally as sufficient information becomes available for each service component, building the BOM progressively during the conversation.
2.  **Handoff**: Once sufficient information is gathered (signaled by a `done: true` completion flag from the Question Agent), the system transitions to the final processing workflow with a complete or near-complete BOM.
3.  **BOM Finalization** (if needed): The **BOM Agent** performs a final review and completes any remaining BOM items.
4.  **Pricing**: The **Pricing Agent** takes the BOM (built incrementally or finalized), queries the Azure Retail Prices API for each item, and calculates monthly costs.
5.  **Proposal**: The **Proposal Agent** synthesizes the requirements, BOM, and pricing into a comprehensive Markdown proposal.

## 4. Functional Requirements

### 4.1. Question Agent (Interactive Chat)
-   **Role**: Solution Architect / Requirement Gatherer.
-   **Input**: User natural language responses.
-   **Capabilities**:
    -   Conduct multi-turn conversation (max 20 turns).
    -   Adapt questions based on workload type (Web, DB, AI/ML, etc.).
    -   Use `microsoft_docs_search` MCP tool to verify service capabilities and region availability.
    -   **Look up recommended Azure architectures** for the workload type and base questions on architectural patterns (e.g., Azure Well-Architected Framework, reference architectures).
    -   **Ask about architecture components** such as private networking, Application Gateway, WAF, API Management, private endpoints, and other components typical of recommended architectures.
-   **Output**: A JSON object wrapped in a ```json code block: `{ "requirements": "<summary>", "done": true }` (no extra text outside the JSON).
-   **Minimum Data Points**: Workload Type, Scale/Size, Specific Service(s), Deployment Region, Architecture Components (networking, gateways, security features).

### 4.2. BOM Agent (Service Mapping)
-   **Role**: Infrastructure Designer.
-   **Input**: Conversation history and requirements summary (can be partial during incremental building).
-   **Operation Modes**:
    -   **Incremental Mode**: Invoked during conversation when Question Agent detects sufficient information for a service component. Analyzes recent conversation context (last 6 exchanges) to identify new services or updates to existing ones.
    -   **Final Mode**: Invoked at completion to review and finalize the complete BOM.
-   **Capabilities**:
    -   Map workloads to appropriate Azure Services (e.g., Web App -> Azure App Service).
    -   Select SKUs based on scale (Small/Basic, Medium/Standard, Large/Premium).
    -   Use `microsoft_docs_search` MCP tool to validate Service Names and SKU identifiers.
    -   Use `azure_sku_discovery` from Azure Pricing MCP for intelligent SKU matching.
    -   **Update existing BOM items** when requirements change (e.g., tier upgrade from Basic to Premium).
    -   **Merge new items** with existing BOM, matching on `serviceName` + `region` for updates.
-   **Trigger Conditions** (Incremental Mode):
    -   Service or configuration keywords detected (e.g., "app service", "database", "sku", "tier")
    -   Every 3 conversation turns to capture accumulated information
    -   Conversation completion (`done: true`)
-   **Output**: Valid JSON array of BOM items (new or updated items in incremental mode, complete BOM in final mode).
    -   Schema: `[{ "serviceName": "...", "sku": "...", "quantity": 1, "region": "...", "armRegionName": "...", "hours_per_month": 730 }]`

### 4.3. Pricing Agent (Cost Estimation)
-   **Role**: Cost Analyst.
-   **Input**: BOM JSON array.
-   **Capabilities**:
    -   Query Azure Pricing MCP server via `MCPStreamableHTTPTool` (endpoint configured via `AZURE_PRICING_MCP_URL` environment variable, defaults to `http://localhost:8080/mcp`).
    -   Available MCP tools:
        -   `azure_cost_estimate`: Primary tool for calculating costs (service_name, sku_name, region, hours_per_month).
        -   `azure_price_search`: Search retail prices with filtering.
        -   `azure_price_compare`: Compare prices across regions or SKUs.
        -   `azure_region_recommend`: Find cheapest regions for a service/SKU.
        -   `azure_discover_skus`: List available SKUs for a service.
        -   `azure_sku_discovery`: Intelligent SKU discovery with fuzzy matching.
        -   `get_customer_discount`: Get customer discount information.
    -   Handle tool failures gracefully (fallback to $0.00 with note).
    -   Calculate total monthly cost by summing item costs (monthly_cost * quantity).
    -   Optionally suggest cost optimization alternatives using `azure_region_recommend`.
-   **Output**: JSON object with itemized costs, total monthly estimate, savings options, and cost optimization suggestions.
    -   **Schema** (authoritative):
            -   `items`: array of objects `{ serviceName, sku, region, armRegionName, quantity, hours_per_month, unit_price, monthly_cost, notes? }`.
            -   `total_monthly`: number (sum of `item.monthly_cost * item.quantity`).
            -   `currency`: string (e.g., "USD").
            -   `pricing_date`: ISO 8601 date string indicating pricing snapshot.
            -   `savings_options`: optional array of objects `{ description, estimated_monthly_savings }`.
            -   `errors`: optional array of strings for lookup failures (use when fallback to $0.00 is applied).
    -   **Example**:
    ```json 
    {
        "items": [
            {
                "serviceName": "Azure App Service",
                "sku": "S1",
                "region": "East US",
                "armRegionName": "eastus",
                "quantity": 2,
                "hours_per_month": 730,
                "unit_price": 0.1,
                "monthly_cost": 146.0,
                "notes": "Fallback to $0.00 if lookup fails"
            }
        ],
        "total_monthly": 292.0,
        "currency": "USD",
        "pricing_date": "2026-01-07",
        "savings_options": [
            {
                "description": "Consider West US for 8% lower rate",
                "estimated_monthly_savings": 12.0
            }
        ],
        "errors": []
    }
    ```

### 4.4. Proposal Agent (Documentation)
-   **Role**: Sales Consultant.
-   **Input**: Requirements, BOM JSON, and Pricing JSON.
-   **Capabilities**:
    -   Synthesize all data into a coherent narrative.
    -   Format output as professional Markdown.
-   **Output Structure**:
    1.  **Executive Summary**: Business need and solution overview.
    2.  **Solution Architecture**: List of services and their roles.
    3.  **Cost Breakdown**: Table of services, SKUs, quantities, and costs.
    4.  **Total Cost Summary**: Monthly and Annual totals.
    5.  **Next Steps**: Deployment and validation recommendations.
    6.  **Assumptions**: Operating hours, region, pricing date.

## 5. Technical Architecture

### 5.1. Technology Stack
-   **Framework**: Microsoft Agent Framework (`agent-framework`, `agent-framework-azure-ai`).
-   **AI Service**: Azure AI Foundry Agent Service.
-   **Language**: Python 3.10+.
-   **External APIs**: 
    -   Azure Pricing MCP Server (`http://localhost:8080/mcp`) - MCP server for pricing data.
    -   Microsoft Learn MCP (`https://learn.microsoft.com/api/mcp`) - Documentation search.
-   **Observability**: OpenTelemetry with Aspire Dashboard integration.

### 5.2. Orchestration
The application uses a hybrid orchestration pattern combining incremental and sequential execution:

1.  **Discovery Stage with Incremental BOM Building**: Interactive chat loop managed by `ChatAgent` with thread-based conversation. During this stage:
    -   Question Agent conducts adaptive Q&A
    -   BOM Agent is invoked incrementally when trigger conditions are met
    -   BOM items are accumulated in session state (`SessionData.bom_items`)
    -   Stage terminates when the Question Agent emits `done: true` in its final JSON response
2.  **Processing Stage**: `SequentialBuilder` pipeline executing agents in order: `BOM Agent (final review)` → `Pricing Agent` → `Proposal Agent`.
    -   BOM Agent performs final validation and completion of BOM (may use incrementally built items)
    -   Pricing Agent processes the complete BOM
    -   Proposal Agent generates final output

### 5.3. Data Flow

**Discovery Stage (Incremental)**:
```
User Input → Question Agent → Trigger Check →
  [If Triggered]:
    Recent Context (6 exchanges) → BOM Agent (Incremental) → 
    Parse & Validate → Merge with Session BOM → Store in SessionData.bom_items
  → Return Response + BOM Items to UI
```

**Processing Stage (Sequential)**:
```
Session BOM Items + Requirements → BOM Agent (Final) → Complete BOM JSON → 
Pricing Agent → Pricing JSON → Proposal Agent → Proposal.md
```

**Complete Flow**:
```
[Discovery: User ↔ Question Agent + Incremental BOM Building] → 
[Processing: BOM Finalization → Pricing → Proposal]
```

### 5.4. Agent Implementation
All agents are implemented using `ChatAgent` from the Microsoft Agent Framework:

| Agent | Tools | Purpose |
|-------|-------|--------|
| Question Agent | `MCPStreamableHTTPTool` (Microsoft Learn) | Gathers requirements through adaptive Q&A |
| BOM Agent | `MCPStreamableHTTPTool` (Microsoft Learn + Azure Pricing MCP) | Maps requirements to Azure services/SKUs |
| Pricing Agent | `MCPStreamableHTTPTool` (Azure Pricing MCP via HTTP) | Calculates costs using MCP pricing tools |
| Proposal Agent | None | Generates professional Markdown proposal |

### 5.5. Client Management
The `AzureAIAgentClient` is used as an async context manager to ensure proper resource cleanup:

```python
async with DefaultAzureCredential() as credential:
    async with AzureAIAgentClient(
        project_endpoint=endpoint,
        async_credential=credential
    ) as client:
        # Run workflows
```

## 6. Non-Functional Requirements
-   **Reliability**: Agents must handle invalid inputs and API timeouts gracefully.
-   **Accuracy**: Pricing must reflect real-time public retail rates.
-   **Performance**: End-to-end processing (after chat) should complete within reasonable time (approx. 30-60s).
-   **Security**: No customer credentials required; uses public pricing API. Azure CLI credentials used for Agent Service authentication.
-   **Observability**: OpenTelemetry tracing enabled for monitoring and debugging.
-   **Testing**: Run end-to-end agent workflow tests, verify Question Agent emits `done: true` with a structured requirements summary, validate BOM JSON against schema, and test pricing agent with live MCP server at `http://localhost:8080/mcp`.

# 7. Enhancements Completed
-   ✅ **Progressive BOM Disclosure**: Users can now see BOM items as they are identified during the conversation (Web UI displays in real-time side panel; CLI builds in background).
-   ✅ **Incremental BOM Building**: BOM is constructed progressively during discovery stage with intelligent triggering and merge logic.

# 8. Planned Enhancements
-   **Tune Questioning Strategy**: Improve adaptive questioning based on workload type and experience level.
-   **Observability Enhancements**: Add more detailed tracing and logging for each step, with log level control.
-   **Progress Feedback**: Provide real-time progress updates during processing stage.
-   **Improve Performance**: Optimize agent response times and MCP tool calls.
-   **Incremental Pricing**: Extend incremental approach to pricing calculation during discovery.
-   **Web Interface**: Allow for retrieval of previous proposals.
-   **Price Citations**: Include links to Azure pricing pages in the proposal for transparency.
-   **Testing**: Implement complete unit and integration tests for each agent and workflow stage.
-   **AI Evaluation**: Set up evaluation framework to assess agent outputs for quality and accuracy.