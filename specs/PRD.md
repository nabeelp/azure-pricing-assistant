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
    -   Use Microsoft Learn MCP tool (`MCPStreamableHTTPTool` at `https://learn.microsoft.com/api/mcp`) to verify service capabilities and region availability.
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
    -   Use Microsoft Learn MCP tool to validate Service Names and SKU identifiers.
    -   Use Azure Pricing MCP tool (provides `azure_sku_discovery`) for intelligent SKU matching.
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
| Question Agent | Microsoft Learn MCP (`MCPStreamableHTTPTool`) | Gathers requirements through adaptive Q&A |
| BOM Agent | Microsoft Learn MCP + Azure Pricing MCP (`MCPStreamableHTTPTool`) | Maps requirements to Azure services/SKUs |
| Pricing Agent | Azure Pricing MCP (`MCPStreamableHTTPTool`) | Calculates costs using MCP pricing tools |
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
| `AZURE_PRICING_MCP_URL` | No | `http://localhost:8080/mcp` | Azure Pricing MCP server endpoint |
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
-   ✅ **Observability Enhancements**: Comprehensive tracing and logging with session spans, stage spans, handler spans, and configurable log levels. Full OpenTelemetry integration with Aspire Dashboard support.
-   ✅ **Progress Feedback (Partial)**: Real-time SSE-based progress updates during proposal generation via `/api/generate-proposal-stream` endpoint. Provides agent start, progress, and completion events.

# 8. Planned Enhancements
-   **Tune Questioning Strategy**: Improve adaptive questioning based on workload type and experience level.
-   **Progress Feedback (UI)**: Integrate streaming progress feedback into the web UI for visual progress indication.
-   **Improve Performance**: Optimize agent response times and MCP tool calls.
-   **Incremental Pricing**: Extend incremental approach to pricing calculation during discovery.
-   **Web Interface**: Allow for retrieval of previous proposals.
-   **Price Citations**: Include links to Azure pricing pages in the proposal for transparency.
-   **Testing**: Implement complete unit and integration tests for each agent and workflow stage.
-   **AI Evaluation**: Set up evaluation framework to assess agent outputs for quality and accuracy.
-   **Metrics**: Add OpenTelemetry metrics (counters for chat turns, proposal generations, errors).
-   **Structured Logging**: Enhance logs with structured data using `extra={}` parameter for better querying.