# Product Requirements Definition (PRD): Azure Seller Assistant

## 1. Overview
The **Azure Seller Assistant** is an AI-powered tool designed to automate the process of gathering customer requirements, designing Azure solutions, estimating costs, and generating professional proposals. It leverages a multi-agent architecture to handle distinct stages of the sales engineering workflow, ensuring accuracy and consistency.

## 2. Goals & Objectives
- **Automate Requirement Gathering**: Replace manual questionnaires with an intelligent, interactive chat interface.
- **Accurate Solution Design**: Automatically map high-level requirements to specific Azure services and SKUs.
- **Real-Time Pricing**: Provide accurate cost estimates using live data from the Azure Retail Prices API.
- **Professional Output**: Generate client-ready proposals in Markdown format without manual formatting.
- **Up-to-Date Knowledge**: Utilize Microsoft Learn documentation to ensure recommendations reflect the latest Azure capabilities.

## 3. User Workflow
1.  **Discovery**: The user initiates a chat session. The **Question Agent** asks adaptive questions to understand the workload, scale, preferred services, and region.
2.  **Handoff**: Once sufficient information is gathered (signaled by "We are DONE!"), the system transitions to the processing phase.
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
    -   Use `microsoft_docs_search` tool to verify service capabilities and region availability.
-   **Output**: A summarized list of requirements ending with the termination phrase "We are DONE!".
-   **Minimum Data Points**: Workload Type, Scale/Size, Specific Service(s), Deployment Region.

### 4.2. BOM Agent (Service Mapping)
-   **Role**: Infrastructure Designer.
-   **Input**: Conversation history and requirements summary.
-   **Capabilities**:
    -   Map workloads to appropriate Azure Services (e.g., Web App -> Azure App Service).
    -   Select SKUs based on scale (Small/Basic, Medium/Standard, Large/Premium).
    -   Use `microsoft_docs_search` to validate Service Names and SKU identifiers.
-   **Output**: Valid JSON array of BOM items.
    -   Schema: `[{ "serviceName": "...", "sku": "...", "quantity": 1, "region": "...", "armRegionName": "...", "hours_per_month": 730 }]`

### 4.3. Pricing Agent (Cost Estimation)
-   **Role**: Cost Analyst.
-   **Input**: BOM JSON array.
-   **Capabilities**:
    -   Query Azure Retail Prices API via `get_azure_price` tool.
    -   Filter by Service Name, SKU, and Region.
    -   Handle API failures gracefully (fallback to $0.00 with note).
    -   Calculate monthly cost (`hourly_rate * quantity * 730`).
-   **Output**: JSON object with itemized costs and total monthly estimate.

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
-   **Framework**: Microsoft Agent Framework (`agent-framework-azure-ai`).
-   **AI Service**: Azure AI Foundry Agent Service.
-   **Language**: Python 3.10+.
-   **External APIs**: Azure Retail Prices API (`https://prices.azure.com/api/retail/prices`).

### 5.2. Orchestration
-   **Phase 1 (Discovery)**: Interactive loop managed by `ChatAgent` or `HandoffBuilder`. Terminates on specific string detection.
-   **Phase 2 (Processing)**: `SequentialBuilder` pipeline executing `BOM Agent` -> `Pricing Agent` -> `Proposal Agent`.

### 5.3. Data Flow
`User Input` -> **Question Agent** -> `Requirements Text` -> **BOM Agent** -> `BOM JSON` -> **Pricing Agent** -> `Pricing JSON` -> **Proposal Agent** -> `Proposal.md`

## 6. Non-Functional Requirements
-   **Reliability**: Agents must handle invalid inputs and API timeouts gracefully.
-   **Accuracy**: Pricing must reflect real-time public retail rates.
-   **Performance**: End-to-end processing (after chat) should complete within reasonable time (approx. 30-60s).
-   **Security**: No customer credentials required; uses public pricing API. Azure CLI credentials used for Agent Service authentication.
