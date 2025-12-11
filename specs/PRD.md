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
1.  **Discovery**: The user initiates a chat session. The **Question Agent** asks adaptive questions to understand the workload, scale, preferred services, and region.
2.  **Handoff**: Once sufficient information is gathered (signaled by "We are DONE!"), the system transitions to the processing workflow.
3.  **BOM Generation**: The **BOM Agent** analyzes the requirements and produces a structured Bill of Materials (JSON).
4.  **Pricing**: The **Pricing Agent** takes the BOM, queries the Azure Retail Prices API for each item, and calculates monthly costs.
5.  **Proposal**: The **Proposal Agent** synthesizes the requirements, BOM, and pricing into a comprehensive Markdown proposal.

## 4. Functional Requirements

### 4.1. Question Agent (Interactive Chat)
-   **Role**: Solution Architect / Requirement Gatherer.
-   **Input**: User natural language responses.
-   **Capabilities**:
    -   Conduct multi-turn conversation (max 20 turns).
    -   Adapt questions based on workload type (Web, DB, AI/ML, etc.).
    -   Use `microsoft_docs_search` MCP tool to verify service capabilities and region availability.
-   **Output**: A summarized list of requirements ending with the termination phrase "We are DONE!".
-   **Minimum Data Points**: Workload Type, Scale/Size, Specific Service(s), Deployment Region.

### 4.2. BOM Agent (Service Mapping)
-   **Role**: Infrastructure Designer.
-   **Input**: Conversation history and requirements summary.
-   **Capabilities**:
    -   Map workloads to appropriate Azure Services (e.g., Web App -> Azure App Service).
    -   Select SKUs based on scale (Small/Basic, Medium/Standard, Large/Premium).
    -   Use `microsoft_docs_search` MCP tool to validate Service Names and SKU identifiers.
-   **Output**: Valid JSON array of BOM items.
    -   Schema: `[{ "serviceName": "...", "sku": "...", "quantity": 1, "region": "...", "armRegionName": "...", "hours_per_month": 730 }]`

### 4.3. Pricing Agent (Cost Estimation)
-   **Role**: Cost Analyst.
-   **Input**: BOM JSON array.
-   **Capabilities**:
    -   Query Azure Pricing MCP server via `MCPStreamableHTTPTool` (SSE endpoint configured via `AZURE_PRICING_MCP_URL` environment variable, defaults to `http://localhost:8080/sse`).
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
    -   Azure Pricing MCP Server (`http://localhost:8080/sse`) - SSE-based MCP server for pricing data.
    -   Microsoft Learn MCP (`https://learn.microsoft.com/api/mcp`) - Documentation search.
-   **Observability**: OpenTelemetry with Aspire Dashboard integration.

### 5.2. Orchestration
The application uses a two-stage orchestration pattern:

1.  **Discovery Stage**: Interactive chat loop managed by `ChatAgent` with thread-based conversation. Terminates when "We are DONE!" is detected in the agent response.
2.  **Processing Stage**: `SequentialBuilder` pipeline executing agents in order: `BOM Agent` → `Pricing Agent` → `Proposal Agent`.

### 5.3. Data Flow
```
User Input → Question Agent → Requirements Text → BOM Agent → BOM JSON → Pricing Agent → Pricing JSON → Proposal Agent → Proposal.md
```

### 5.4. Agent Implementation
All agents are implemented using `ChatAgent` from the Microsoft Agent Framework:

| Agent | Tools | Purpose |
|-------|-------|--------|
| Question Agent | `MCPStreamableHTTPTool` (Microsoft Learn) | Gathers requirements through adaptive Q&A |
| BOM Agent | `MCPStreamableHTTPTool` (Microsoft Learn + Azure Pricing MCP) | Maps requirements to Azure services/SKUs |
| Pricing Agent | `MCPStreamableHTTPTool` (Azure Pricing MCP via SSE) | Calculates costs using MCP pricing tools |
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
