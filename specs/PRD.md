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

### 4.1. Architect Agent (Interactive Azure Solutions Architect)
-   **Role**: Azure Solutions Architect / Requirement Gatherer with progressive service identification.
-   **Input**: User natural language responses.
-   **Capabilities**:
    -   Conduct multi-turn conversation (max 20 turns).
    -   Adapt questions based on workload type (Web, DB, AI/ML, etc.).
    -   Use Microsoft Learn MCP tool (`MCPStreamableHTTPTool` at `https://learn.microsoft.com/api/mcp`) to verify service capabilities and region availability.
    -   **Use static service catalog** with common Azure services and SKUs for real-time service recommendations.
    -   **Progressively build Bill of Materials** as information is gathered, maintaining a running list of identified services.
    -   **Look up recommended Azure architectures** for the workload type and base questions on architectural patterns (e.g., Azure Well-Architected Framework, reference architectures).
    -   **Ask about architecture components** such as private networking, Application Gateway, WAF, API Management, private endpoints, and other components typical of recommended architectures.
    -   **Store BOM items directly** in SessionData.bom_items during conversation (no separate incremental BOM agent).
-   **Tools Available**:
    -   `microsoft_docs_search`: Query Microsoft/Azure documentation
    -   Static service catalog: Built-in catalog of 12+ common Azure services with typical SKUs
-   **Service Discovery Approach**:
    1. **Service Identification**: Use static catalog to match workload requirements to Azure services
    2. **SKU Recommendation**: Recommend appropriate SKUs based on scale requirements (Basic/Standard/Premium)
    3. **Validation**: Use Microsoft Learn MCP to validate service capabilities and region availability
    4. **Selection**: Present options to user and gather specific preferences
-   **Output Formats**:
    -   **During conversation**: May include partial BOM JSON with identified services in `identified_services` format
    -   **At completion**: JSON object wrapped in ```json code block: `{ "requirements": "<summary>", "done": true, "bom_items": [...] }`
-   **Minimum Data Points**: Workload Type, Scale/Size, Specific Service(s), Deployment Region, Architecture Components (networking, gateways, security features).

### 4.2. BOM Agent (Service Mapping) - **DEPRECATED**
-   **Status**: Deprecated - functionality moved to Architect Agent (4.1).
-   **Legacy Role**: Infrastructure Designer with incremental and final operation modes.
-   **Note**: Code remains for backward compatibility but is not invoked by orchestrator. The Architect Agent now handles service identification and BOM building directly during conversation using a static service catalog.
-   **Migration**: All BOM generation now happens in the Architect Agent, which:
    -   Uses static service catalog for real-time SKU matching
    -   Maintains progressive BOM in SessionData.bom_items
    -   Stores items directly without separate incremental workflow
-   **Schema**: BOM item schema remains unchanged: `[{ "serviceName": "...", "sku": "...", "quantity": 1, "region": "...", "armRegionName": "...", "hours_per_month": 730 }]`

### 4.3. Pricing Agent (Cost Estimation)
-   **Role**: Cost Analyst using browser automation.
-   **Input**: BOM JSON array.
-   **Capabilities**:
    -   Automate the official Azure Pricing Calculator website via Playwright MCP (`https://azure.microsoft.com/en-us/pricing/calculator/`).
    -   Available Playwright MCP tools:
        -   `browser_navigate`: Navigate to calculator URL
        -   `browser_snapshot`: Get page structure via accessibility tree
        -   `browser_click`: Click elements (add service, configure options)
        -   `browser_type`: Enter text in input fields
        -   `browser_select_option`: Select dropdown options
        -   `browser_fill_form`: Fill multiple form fields at once
    -   **Calculator Automation Workflow**:
        1. Navigate to Azure Pricing Calculator
        2. For each BOM item: Search service → Add to estimate → Configure SKU/region/quantity
        3. Extract pricing data from calculator output
        4. Parse into standard pricing JSON format
    -   **Complex Service Support**: Properly handles AKS clusters with node pools (the primary use case)
    -   Handle tool failures gracefully (fallback to $0.00 with note).
    -   Calculate total monthly cost by summing item costs (monthly_cost * quantity).
-   **Transport Configuration**:
    -   Local development: Uses STDIO transport (`PLAYWRIGHT_MCP_TRANSPORT=stdio`)
    -   Deployed environments: Uses HTTP transport via Container App (`PLAYWRIGHT_MCP_TRANSPORT=http`, `PLAYWRIGHT_MCP_URL`)
-   **Output**: JSON object with itemized costs, total monthly estimate, savings options, and cost optimization suggestions.
    -   **Schema** (authoritative - unchanged from previous version):
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
                "unit_price": 0.10,
                "monthly_cost": 146.00
            }
        ],
        "total_monthly": 292.00,
        "currency": "USD",
        "pricing_date": "2026-01-09",
        "savings_options": [
            {
                "description": "Consider West US for 8% lower rate",
                "estimated_monthly_savings": 12.00
            }
        ],
        "errors": []
    }
    ```
    -   **Note on Fallback Pricing**: When a pricing lookup fails, set `unit_price` and `monthly_cost` to `0.00` and add an error description to the `errors` array.

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

### 4.5. Web UI (Incremental BOM Display)
-   **Live BOM Panel**: The Bill of Materials must appear in the **BOM side panel** while the user answers questions.
-   **Placement**: The BOM panel is the dedicated UI area separate from the chat thread; chat messages remain in the main chat pane.
-   **Real-Time Updates**: As incremental BOM updates complete, the panel should refresh to show new/updated items without requiring a page refresh.
-   **Status Feedback**: The BOM panel should reflect processing states (queued/processing/complete/error) so users understand when updates are in progress.

## 5. Technical Architecture

### 5.1. Technology Stack
-   **Framework**: Microsoft Agent Framework (`agent-framework`, `agent-framework-azure-ai`).
-   **AI Service**: Azure AI Foundry Agent Service.
-   **Language**: Python 3.10+.
-   **External APIs**: 
    -   Playwright MCP Server (STDIO for local, HTTP for deployed) - Browser automation for pricing calculator.
    -   Microsoft Learn MCP (`https://learn.microsoft.com/api/mcp`) - Documentation search.
-   **Observability**: OpenTelemetry with Aspire Dashboard integration.

### 5.2. Orchestration
The application uses a simplified orchestration pattern with progressive BOM building:

1.  **Discovery Stage with Progressive BOM Building**: Interactive chat loop managed by `ChatAgent` with thread-based conversation. During this stage:
    -   Architect Agent conducts adaptive Q&A and progressive service identification
    -   Architect Agent uses `azure_sku_discovery` to match requirements to SKUs in real-time
    -   BOM items are built and stored directly by Architect Agent in session state (`SessionData.bom_items`)
    -   Partial BOM items extracted from architect responses after each turn
    -   Stage terminates when the Architect Agent emits `done: true` with final `bom_items` in its JSON response
2.  **Processing Stage**: `SequentialBuilder` pipeline executing agents in order: `Pricing Agent` → `Proposal Agent`.
    -   Pricing Agent processes the BOM items from SessionData
    -   Proposal Agent generates final output
    -   Note: BOM Agent deprecated - BOM generation handled by Architect Agent during discovery

### 5.3. Data Flow

**Discovery Stage (Progressive BOM Building)**:
```
User Input → Architect Agent (with azure_sku_discovery) → 
  Extract partial BOM JSON from response → 
  Merge with Session BOM → Store in SessionData.bom_items →
  Return Response + Updated BOM Items to UI
```

**Processing Stage (Sequential)**:
```
Session BOM Items + Requirements → Pricing Agent → Pricing JSON → 
Proposal Agent → Proposal.md
```

**Complete Flow**:
```
[Discovery: User ↔ Architect Agent with Progressive BOM Building] → 
[Processing: Pricing → Proposal]
```

### 5.4. Agent Implementation
All agents are implemented using `ChatAgent` from the Microsoft Agent Framework:

| Agent | Tools | Purpose |
|-------|-------|--------|
| Architect Agent | Microsoft Learn MCP (`MCPStreamableHTTPTool`) | Gathers requirements through adaptive Q&A and builds BOM progressively using static service catalog |
| BOM Agent (Deprecated) | Microsoft Learn MCP (`MCPStreamableHTTPTool`) | Legacy - functionality moved to Architect Agent |
| Pricing Agent | Playwright MCP (`MCPStreamableHTTPTool` or STDIO) | Automates Azure Pricing Calculator for accurate cost estimates |
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

### 5.6. Web API Endpoints
The Flask web application exposes the following REST API endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Render main chat UI page |
| `/api/chat` | POST | Handle chat message, returns response with incremental BOM updates |
| `/api/generate-proposal` | POST | Generate full proposal (blocking) |
| `/api/generate-proposal-stream` | GET | Generate proposal with SSE streaming progress events |
| `/api/bom` | GET | Get current BOM items for the session |
| `/api/history` | GET | Get chat history for the session |
| `/api/reset` | POST | Reset chat session and clear state |
| `/health` | GET | Health check endpoint |

**SSE Progress Events** (`/api/generate-proposal-stream`):
-   `agent_start`: Agent begins processing (includes `agent_name`)
-   `agent_progress`: Agent emits progress text (includes `message`)
-   `workflow_complete`: All agents complete (includes `data` with `bom`, `pricing`, `proposal`)
-   `error`: Error occurred during processing (includes `message`)

## 6. Non-Functional Requirements
-   **Reliability**: Agents must handle invalid inputs and API timeouts gracefully.
-   **Accuracy**: Pricing must reflect real-time public retail rates.
-   **Performance**: End-to-end processing (after chat) should complete within reasonable time (approx. 30-60s).
-   **Security**: No customer credentials required; uses public pricing API. Azure CLI credentials used for Agent Service authentication.
-   **Observability**: Comprehensive OpenTelemetry tracing with Aspire Dashboard integration (see Section 6.1).
-   **Testing**: Run end-to-end agent workflow tests, verify Question Agent emits `done: true` with a structured requirements summary, validate BOM JSON against schema, and test pricing agent with live MCP server at `http://localhost:8080/mcp`.

### 6.1. Observability Architecture
The application implements a layered observability approach:

**Tracing:**
-   **Agent Framework Integration**: Uses `setup_observability()` from Agent Framework for OTLP export of traces and logs.
-   **Session Spans**: Long-lived OpenTelemetry spans per user session (CLI and Web) enabling correlation of all operations within a session.
-   **Stage Spans**: Workflow stages (Question, BOM, Pricing, Proposal) emit individual spans via `_stage_span()` helper.
-   **Handler Spans**: Handler operations (`chat_turn`, `proposal_generation`) emit spans via `_handler_span()` for detailed request tracing.
-   **Span Lifecycle**: Session spans are automatically closed after proposal generation or session reset.

**Logging:**
-   **Console Logging**: Standard Python logs with `trace_id`/`span_id` correlation fields via `TraceContextFilter`.
-   **Log Format**: `%(asctime)s - %(name)s - %(levelname)s - %(message)s [trace_id=%(trace_id)s span_id=%(span_id)s]`
-   **Configurable Level**: `APP_LOG_LEVEL` environment variable controls verbosity (DEBUG, INFO, WARNING, ERROR).
-   **OTLP Export**: Logs are exported to OTLP endpoint when `ENABLE_OTEL=true` and `OTLP_ENDPOINT` (or `OTEL_EXPORTER_OTLP_ENDPOINT`) are set.

**Configuration:**
-   `ENABLE_OTEL`: Enable/disable OpenTelemetry export (default: false). Read by Agent Framework's `setup_observability()`.
-   `OTLP_ENDPOINT` or `OTEL_EXPORTER_OTLP_ENDPOINT`: OTLP collector endpoint (e.g., `http://localhost:4317`). Agent Framework reads `OTLP_ENDPOINT`; standard OTel SDK reads `OTEL_EXPORTER_OTLP_ENDPOINT`.
-   `OTEL_EXPORTER_OTLP_TRACES_INSECURE`: Set to `true` when using HTTP (non-TLS) OTLP endpoint.
-   `OTLP_HEADERS` or `OTEL_EXPORTER_OTLP_HEADERS`: OTLP headers for authentication (e.g., `Authorization=Bearer <token>`).
-   `OTEL_SERVICE_NAME`: Service name for traces (defaults to `azure-pricing-assistant-web` or `azure-pricing-assistant-cli`).
-   `APP_LOG_LEVEL`: Console log verbosity (default: INFO).

**Required Environment Variables:**
| Variable | Required | Default | Purpose |
|----------|----------|---------|--------|
| `AZURE_AI_PROJECT_ENDPOINT` | Yes | — | Azure AI Foundry project endpoint |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | No | `gpt-4o-mini` | Azure AI model deployment name |
| `PLAYWRIGHT_MCP_TRANSPORT` | No | `stdio` | Transport type: 'stdio' (local) or 'http' (deployed) |
| `PLAYWRIGHT_MCP_URL` | No | `http://localhost:8080` | Playwright MCP HTTP endpoint (only for http transport) |
| `FLASK_SECRET_KEY` | Yes (web) | — | Flask session secret key |
| `PORT` | No | `8000` | Local web server port |
| `ENABLE_OTEL` | No | `false` | Enable/disable OpenTelemetry export |
| `OTLP_ENDPOINT` | No | — | OTLP collector endpoint (Agent Framework alias) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | No | — | OTLP collector endpoint (standard OTel) |
| `OTLP_HEADERS` | No | — | OTLP headers for authentication |
| `OTEL_SERVICE_NAME` | No | `azure-pricing-assistant-*` | Service name for traces |
| `APP_LOG_LEVEL` | No | `INFO` | Console log verbosity (DEBUG, INFO, WARNING, ERROR) |

# 7. Enhancements Completed
-   ✅ **Progressive BOM Disclosure**: Users can now see BOM items as they are identified during the conversation (Web UI displays in real-time side panel; CLI builds in background).
-   ✅ **Incremental BOM Building**: BOM is constructed progressively during discovery stage with intelligent triggering and merge logic.
-   ✅ **Architect Agent with Real-time SKU Discovery**: Refactored Question Agent into Architect Agent that uses `azure_sku_discovery` during conversation to identify services and SKUs in real-time. Builds BOM progressively without separate incremental BOM agent.
-   ✅ **BOM Agent Deprecation**: Incremental BOM agent functionality moved to Architect Agent for simplified orchestration and better conversation context.
-   ✅ **Observability Enhancements**: Comprehensive tracing and logging with session spans, stage spans, handler spans, and configurable log levels. Full OpenTelemetry integration with Aspire Dashboard support.
-   ✅ **Progress Feedback (Partial)**: Real-time SSE-based progress updates during proposal generation via `/api/generate-proposal-stream` endpoint. Provides agent start, progress, and completion events.

# 8. Planned Enhancements
-   **Tune Questioning Strategy**: Further refine Architect Agent's adaptive questioning based on workload type and experience level.
-   **Progress Feedback (UI)**: Integrate streaming progress feedback into the web UI for visual progress indication.
-   **Improve Performance**: Optimize agent response times and MCP tool calls.
-   **Incremental Pricing**: Extend incremental approach to pricing calculation during discovery.
-   **Web Interface**: Allow for retrieval of previous proposals.
-   **Price Citations**: Include links to Azure pricing pages in the proposal for transparency.
-   **Testing**: Implement complete unit and integration tests for each agent and workflow stage.
-   **AI Evaluation**: Set up evaluation framework to assess agent outputs for quality and accuracy.
-   **Metrics**: Add OpenTelemetry metrics (counters for chat turns, proposal generations, errors).
-   **Structured Logging**: Enhance logs with structured data using `extra={}` parameter for better querying.
-   **BOM Agent Removal**: Remove deprecated BOM agent code in future cleanup PR.