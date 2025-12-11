# GitHub Copilot Instructions for Azure Pricing Assistant

## Project Context

This is an AI-powered Azure pricing solution built with Microsoft Agent Framework. The solution uses a multi-agent workflow to gather requirements, generate Bill of Materials (BOM), calculate pricing, and create proposals.

## Required Reading

**CRITICAL**: Before making any changes to agent code or instructions, you MUST reference the Product Requirements Definition:

- **`specs/PRD.md`** - The single source of truth for all agent behaviors, prompts, architecture, and API specifications.

## Agent Implementation Rules

### 1. Agent Instructions Fidelity
When implementing or modifying agent code:
- Reference the "Functional Requirements" section in `specs/PRD.md`.
- Ensure agent prompts align with the roles and capabilities defined in the PRD.
- Maintain strict adherence to the input/output schemas defined in the PRD.

### 2. Workflow Orchestration
- **Question Agent**: Uses `ChatAgent` with thread-based conversation. Terminates when "We are DONE!" is detected.
- **Processing Pipeline**: Uses `SequentialBuilder` for BOM → Pricing → Proposal agents.
- Follow the orchestration patterns defined in `specs/PRD.md`.

### 3. Agent Tools
- **Question Agent & BOM Agent**: Use `MCPStreamableHTTPTool` for Microsoft Learn documentation access.
- **Pricing Agent**: Uses `MCPStreamableHTTPTool` for Azure Pricing MCP server (SSE at `http://localhost:8080/sse`).
- **Proposal Agent**: No tools (pure text synthesis).

### 4. Data Schemas
- **BOM JSON**: Must match the schema defined in the PRD (Section 4.2).
- **Pricing Output**: Must match the schema defined in the PRD (Section 4.3).
- **Proposal**: Must follow the markdown structure defined in the PRD (Section 4.4).

### 5. API Integration
- Use Azure Pricing MCP server at `http://localhost:8080/sse` (SSE transport).
- Available MCP tools: `azure_cost_estimate`, `azure_price_search`, `azure_price_compare`, `azure_region_recommend`, `azure_discover_skus`, `azure_sku_discovery`, `get_customer_discount`.
- Follow the API usage guidelines in `specs/PRD.md`.
- Handle errors gracefully (return 0.0 for missing pricing data).

### 6. Code Organization
```
app.py                  # Flask web application entry point
main.py                 # CLI entry point (legacy)
templates/
└── index.html         # Web UI for chat interface
src/
├── agents/
│   ├── question_agent.py
│   ├── bom_agent.py
│   ├── pricing_agent.py
│   └── proposal_agent.py
infra/
├── main.bicep         # Azure infrastructure definition
├── resources.bicep    # Resource definitions
└── main.parameters.json  # Deployment parameters
    └── __init__.py
```

### 7. Testing Requirements
- All agent changes must be tested end-to-end.
- Verify "We are DONE!" termination for Question Agent.
- Validate JSON schema compliance for BOM output.
- Test pricing MCP integration with running MCP server at `http://localhost:8080/sse`.
- Review proposal output quality against PRD standards.

## Common Tasks

### Creating/Modifying an Agent
1. Read the relevant agent section in `specs/PRD.md`.
2. Implement using `ChatAgent` from the agent framework.
3. Ensure instructions reflect the "Capabilities" and "Role" defined in the PRD.
4. Use appropriate tools (`MCPStreamableHTTPTool` for docs, `AIFunction` for API calls).

### Updating Agent Instructions
1. If the change represents a requirement change, update `specs/PRD.md` first.
2. Update the agent implementation to reflect the new requirements.
3. Test the change end-to-end.

## Quality Standards

### Code Quality
- Use async/await patterns (Microsoft Agent Framework is async).
- Include type hints for function signatures.
- Add error handling for API calls and JSON parsing.
- Log important events and errors.
- Follow Python PEP 8 style guidelines.

## Termination Signal

**CRITICAL**: The Question Agent MUST output exactly "We are DONE!" (case-sensitive, with exclamation mark) to signal completion. This text:
- Must appear in the agent's final response.
- Triggers the workflow termination condition.
- Must not appear in intermediate responses.
- Is detected by: `any("We are DONE!" in msg.text for msg in conv if msg.role.value == "assistant")`

## Getting Started

When starting work on this project:
1. Read `specs/PRD.md` for system overview, agent roles, and technical architecture.
2. Review the "Functional Requirements" to understand the specific duties of each agent.

## Azure Deployment

### Deployment Architecture
This application is designed to run on Azure using Azure Developer CLI (azd):

- **Hosting**: Azure App Service (Linux, Python 3.11)
- **Compute**: App Service Plan (configurable SKU, default: B1)
- **Monitoring**: Application Insights with Log Analytics Workspace
- **Authentication**: Managed Identity for Azure AI Foundry access
- **Infrastructure**: Bicep templates in `infra/` directory

### Deployment Workflow

#### Prerequisites
1. Install Azure Developer CLI: `brew install azd` (macOS) or [download](https://aka.ms/install-azd)
2. Install Azure CLI: `brew install azure-cli` (macOS)
3. Ensure you have:
   - Azure subscription with appropriate permissions
   - Azure AI Foundry project endpoint configured

#### Initial Deployment
```bash
# 1. Login to Azure
azd auth login
az login

# 2. Initialize environment (first time only)
azd env new <environment-name>

# 3. Set required configuration
azd env set AZURE_AI_PROJECT_ENDPOINT "<your-ai-foundry-endpoint>"

# 4. Optional: Change App Service Plan SKU (default: B1)
azd env set APP_SERVICE_PLAN_SKU "S1"

# 5. Preview deployment
azd provision --preview

# 6. Deploy infrastructure and application
azd up
```

#### Subsequent Deployments
```bash
# Deploy code changes only
azd deploy

# Deploy infrastructure changes
azd provision

# Deploy both
azd up
```

#### Environment Management
```bash
# View current environment
azd env list

# Get environment values
azd env get-values

# Delete environment
azd down
```

### Azure Resources Created

The deployment creates:
1. **Resource Group**: `rg-<env>-<token>`
2. **App Service Plan**: `asp-<env>-<token>` (Linux, configurable SKU)
3. **App Service**: `app-<env>-<token>` (Python 3.11, System-Assigned Managed Identity)
4. **Application Insights**: `appi-<env>-<token>`
5. **Log Analytics Workspace**: `log-<env>-<token>`

### Configuration

#### Required Environment Variables
- `AZURE_AI_PROJECT_ENDPOINT`: Azure AI Foundry project endpoint (configured via App Settings)
- `APPLICATIONINSIGHTS_CONNECTION_STRING`: Auto-configured by deployment
- `FLASK_SECRET_KEY`: Auto-generated or can be set manually

#### App Service Configuration
The App Service is configured with:
- **Runtime**: Python 3.11 on Linux
- **Startup Command**: Uses Gunicorn with 4 workers
- **Authentication**: System-Assigned Managed Identity enabled
- **Security**: HTTPS only, TLS 1.2 minimum, FTPS disabled
- **Build**: Oryx build enabled for automatic dependency installation

### Monitoring and Debugging

#### View Logs
```bash
# Stream application logs
az webapp log tail --name <app-name> --resource-group <rg-name>

# View logs in Azure Portal
# Navigate to: App Service → Monitoring → Log stream
```

#### Application Insights
- **Traces**: OpenTelemetry integration for distributed tracing
- **Metrics**: Request rates, response times, failure rates
- **Logs**: Application logs and exceptions

#### Health Check
The application exposes a `/health` endpoint for monitoring.

### Infrastructure as Code Guidelines

When modifying Bicep templates:
1. **Follow Bicep Best Practices**: Use symbolic references, avoid hardcoded resourceIds
2. **Security First**: Never disable security features (e.g., purge protection, anonymous access)
3. **Latest API Versions**: Always use the most recent stable API versions
4. **Parameterization**: Use parameters for environment-specific values
5. **Managed Identity**: Prefer managed identity over credentials
6. **Location**: Place all Bicep files in `infra/` directory

### Web Application Guidelines

When modifying the Flask application:
1. **Session Management**: Use server-side sessions (Redis recommended for production)
2. **Error Handling**: Implement proper error handling for all API endpoints
3. **Security**: Set `FLASK_SECRET_KEY` securely (use Key Vault in production)
4. **Async Operations**: Use proper async/await patterns with event loops
5. **Resource Cleanup**: Ensure proper cleanup of Azure clients and threads

### Deployment Best Practices

1. **Test Locally First**: Test changes locally before deploying
2. **Preview Changes**: Always use `--preview` flag with `azd provision`
3. **Incremental Deployment**: Use `azd deploy` for code-only changes
4. **Monitor Deployments**: Check Application Insights after deployment
5. **Environment Isolation**: Use separate environments for dev/test/prod
6. **Configuration Management**: Store secrets in Azure Key Vault
7. **Managed Identity Permissions**: Ensure the App Service managed identity has required permissions for Azure AI Foundry

## Questions or Uncertainties

If agent behavior is unclear:
1. Check `specs/PRD.md` - it is the source of truth.
2. If the PRD is ambiguous, ask for clarification before implementing.

If deployment issues occur:
1. Check deployment logs: `azd deploy --debug`
2. Verify environment variables: `azd env get-values`
3. Review App Service logs: `az webapp log tail`
4. Validate managed identity permissions
