# Azure Pricing Assistant

AI-powered Azure pricing solution using Microsoft Agent Framework with multi-agent workflow for requirements gathering, BOM generation, pricing calculation, and proposal creation.

**🌐 Web Application**: Access through a modern web interface for interactive chat-based requirements gathering and proposal generation.

**☁️ Azure Deployment**: Designed to run on Azure App Service with full infrastructure as code using Azure Developer CLI (azd).

## 🚀 Quick Start

### Azure Deployment (5 Minutes)

Deploy the application to Azure:

```bash
# 1. Login to Azure
azd auth login
az login

# 2. Initialize environment
azd env new <your-environment-name>

# 3. Set your Azure AI Foundry endpoint
azd env set AZURE_AI_PROJECT_ENDPOINT "<your-ai-foundry-endpoint>"

# 4. Optional: Change App Service Plan SKU (default: B1)
azd env set APP_SERVICE_PLAN_SKU "S1"

# 5. Preview the deployment
azd provision --preview

# 6. Deploy infrastructure and application
azd up
```

After deployment completes, you'll receive:
- **Web App URL**: `https://app-<env>-<token>.azurewebsites.net`
- **Resource Group**: View in Azure Portal
- **Application Insights**: Monitor application performance

### Update Deployment

```bash
# Deploy code changes only
azd deploy

# Deploy infrastructure and code changes
azd up

# View environment configuration
azd env get-values

# Clean up all resources
azd down
```

## Architecture

The solution uses a two-stage orchestration pattern:

1. **Discovery Stage**: Interactive chat with the Question Agent to gather requirements
2. **Processing Stage**: Sequential workflow executing BOM → Pricing → Proposal agents

### Agents

| Agent | Tools | Purpose |
|-------|-------|--------|
| **Question Agent** | Microsoft Learn MCP | Gathers requirements through adaptive Q&A (max 20 turns) |
| **BOM Agent** | Microsoft Learn MCP + Azure Pricing MCP | Maps requirements to Azure services and SKUs |
| **Pricing Agent** | Azure Pricing MCP | Calculates real-time costs for each BOM item |
| **Proposal Agent** | None | Generates professional Markdown proposal |

## Optional Dependencies

This project uses pip extras for optional dependencies:

| Extra | Description | Use Case |
|-------|-------------|----------|
| `[web]` | Flask + Gunicorn | Web interface (production and local) |
| `[cli]` | No additional deps | Command-line interface |
| `[dev]` | Testing & linting tools | Development and testing |
| `[all]` | All of the above | Full installation |

**Installation examples:**
```bash
pip install -e .          # Core dependencies only
pip install -e .[web]     # Web interface
pip install -e .[cli]     # CLI interface  
pip install -e .[dev]     # Development
pip install -e .[all]     # Everything
```

## Prerequisites

### For Local Development
- Python 3.10 or higher
- Azure CLI installed and authenticated (`az login`)
- Azure AI Foundry project endpoint
- Azure Pricing MCP Server running locally (HTTP endpoint, see [Azure Pricing MCP](https://github.com/nabeelp/AzurePricingMCP/tree/streamable-http))

### For Azure Deployment
- [Azure Developer CLI (azd)](https://aka.ms/install-azd) installed
- [Azure CLI](https://docs.microsoft.com/cli/azure/install-azure-cli) installed
- Azure subscription with appropriate permissions
- Azure AI Foundry project endpoint configured

## Environment Variables

| Name | Required | Default | Notes |
|------|----------|---------|-------|
| AZURE_AI_PROJECT_ENDPOINT | Yes | — | Azure AI Foundry project endpoint used by AzureAIAgentClient |
| AZURE_PRICING_MCP_URL | No | http://localhost:8080/mcp | Endpoint for Azure Pricing MCP (used by BOM and Pricing agents) |
| FLASK_SECRET_KEY | Yes for web | — | Secret key for Flask sessions |
| PORT | No | 8000 | Port for local web server |

## Local Development Setup

1. **Clone repository**
   ```bash
   git clone <repository-url>
   cd azure-seller-assistant
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   
   Choose the installation based on your needs:
   ```bash
   # For web interface (recommended)
   pip install -e .[web]
   
   # For CLI interface only
   pip install -e .[cli]
   
   # For development (includes all dependencies + dev tools)
   pip install -e .[dev]
   
   # Or install all optional dependencies
   pip install -e .[all]
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and set:
   - `AZURE_AI_PROJECT_ENDPOINT`: Azure AI Foundry project endpoint (required)
   - `AZURE_PRICING_MCP_URL`: Azure Pricing MCP endpoint (default: http://localhost:8080/mcp)
   - `FLASK_SECRET_KEY`: Secret key for Flask sessions (required for web interface)
   - `PORT`: Optional port override for the local web server (default: 8000)

5. **Authenticate with Azure**
   ```bash
   az login
   ```

6. **Start Azure Pricing MCP Server**
   
   Follow the instructions in the [Azure Pricing MCP repository](https://github.com/nabeelp/AzurePricingMCP/tree/streamable-http) to start the MCP server locally. The agents expect the endpoint at `http://localhost:8080/mcp` (configure via `AZURE_PRICING_MCP_URL`).

7. **Optional - Start Aspire Dashboard for Observability**
   ```bash
   docker run --rm -it -p 18888:18888 -p 4317:18889 --name aspire-dashboard mcr.microsoft.com/dotnet/aspire-dashboard:latest
   ```
   Access the dashboard at http://localhost:18888 to view OpenTelemetry traces.

## Usage

### Web Application (Recommended)

Start the Flask web server:

```bash
python -m src.web.app
```

Open your browser to http://localhost:8000 to access the interactive web interface.

### CLI Application (Legacy)

Run the command-line version:

```bash
python -m src.cli.app
```

The application will:
1. Start an interactive chat session to gather your Azure requirements
2. Ask adaptive questions about workload type, scale, services, and region
3. Generate a Bill of Materials (BOM) based on your requirements
4. Calculate real-time pricing using the Azure Retail Prices API
5. Create a professional proposal document

### Example Interaction

```
=== Starting Requirements Gathering ===

Agent: Hello! I'm here to help you design and price an Azure solution. Let's start by 
understanding your needs.

What type of workload are you looking to run on Azure? For example:
- Web application
- Database
- Data analytics
- Machine learning
- IoT solution

You: Web application for e-commerce

Agent: Great! An e-commerce web application. To help size the solution appropriately, 
could you tell me about your expected scale? For example:
- How many concurrent users do you expect?
- What's your expected daily traffic?

You: About 5000 daily users

Agent: For an e-commerce application with 5000 daily users, you'll need a reliable 
web hosting solution and database. Do you have any specific Azure services in mind, 
or would you like me to recommend appropriate services?

You: Please recommend services

Agent: Which Azure region would you prefer for deployment?

You: East US

Agent: Based on our conversation, here's a summary of your requirements:

**Requirements Summary:**
- **Workload Type**: E-commerce web application
- **Expected Scale**: ~5,000 daily users
- **Recommended Services**: Azure App Service, Azure SQL Database
- **Deployment Region**: East US

```json
{
   "requirements": "Workload: e-commerce web app; Scale: ~5,000 daily users; Services: Azure App Service, Azure SQL Database; Region: East US",
   "done": true
}

✅ Requirements gathering complete (done=true)!

=== Starting BOM → Pricing → Proposal Workflow ===

Processing requirements through agents...

=== Final Proposal ===

# Azure Solution Proposal

## Executive Summary
Based on your requirements for an e-commerce web application serving approximately 
5,000 daily users, we recommend a solution built on Azure App Service and Azure SQL 
Database deployed in the East US region...

## Cost Breakdown
| Service | SKU | Quantity | Hourly Rate | Monthly Cost |
|---------|-----|----------|-------------|--------------|
| Azure App Service | P1v2 | 1 | $0.10 | $73.00 |
| Azure SQL Database | S1 | 1 | $0.03 | $21.90 |

**Total Monthly Cost**: $94.90
**Total Annual Cost**: $1,138.80
```

## Project Structure

```
azure-seller-assistant/
├── azure.yaml
├── pyproject.toml
├── requirements.txt
├── README.md
├── specs/
│   └── PRD.md                     # Product Requirements Definition
├── infra/
│   ├── main.bicep                 # Azure infrastructure definition
│   ├── resources.bicep            # Resource definitions
│   └── main.parameters.json       # Deployment parameters
├── src/
│   ├── agents/                    # AI agents
│   │   ├── bom_agent.py           # Bill of Materials generation
│   │   ├── pricing_agent.py       # Cost calculation via Azure Pricing MCP
│   │   ├── proposal_agent.py      # Professional proposal generation
│   │   └── question_agent.py      # Interactive requirements gathering
│   ├── cli/                       # Command-line interface
│   │   ├── app.py                 # CLI entry point
│   │   ├── interface.py           # CLI implementation
│   │   └── prompts.py             # CLI formatting utilities
│   ├── core/                      # Shared orchestration and configuration
│   │   ├── config.py              # Environment and app configuration
│   │   ├── models.py              # Shared data models
│   │   ├── orchestrator.py        # Workflow orchestration logic
│   │   └── session.py             # Session storage abstraction
│   ├── interfaces/                # Interface abstraction layer
│   │   ├── base.py                # Abstract PricingInterface base class
│   │   ├── context.py             # Execution context management
│   │   └── handlers.py            # Shared workflow handlers
│   ├── shared/                    # Shared utilities
│   │   ├── errors.py              # Custom exception hierarchy
│   │   └── logging.py             # Unified logging setup
│   └── web/                       # Web interface
│       ├── app.py                 # Flask application setup and routes
│       ├── handlers.py            # HTTP endpoint handlers
│       ├── interface.py           # WebInterface implementation
│       ├── models.py              # Request/response models
│       └── templates/
│           └── index.html         # Web UI for chat interface
├── tests/
│   ├── test_bom_agent.py
│   ├── test_bom_integration.py
│   └── test_pricing_agent.py
└── .env.example
```

### Key Architectural Improvements

This codebase uses a **layered architecture** with clear separation of concerns:

1. **Core Layer** (`src/core/`) - Orchestration, configuration, session management
   - Completely interface-agnostic
   - Reusable by any interface implementation

2. **Agent Layer** (`src/agents/`) - AI agent implementations
   - No dependencies on Flask or CLI
   - Pure business logic

3. **Interface Abstraction** (`src/interfaces/`) - Shared contracts and logic
   - `PricingInterface` - Abstract base for all interfaces
   - `InterfaceContext` - Resource management (Azure AI client, sessions)
   - `WorkflowHandler` - Shared business logic used by all interfaces

4. **Interface Implementations**
   - `src/cli/` - Command-line interface
   - `src/web/` - Flask web application
   - Both extend `PricingInterface` and use `WorkflowHandler`

5. **Shared Utilities** (`src/shared/`) - Common helpers
   - Exception definitions
   - Logging configuration

This design **eliminates code duplication** between CLI and Web interfaces while making it easy to add new interfaces (REST API, Slack bot, etc.).

## Documentation

- **Product Requirements**: [specs/PRD.md](specs/PRD.md)
- **GitHub Copilot Instructions**: [.github/copilot-instructions.md](.github/copilot-instructions.md)

## Features

- ✅ **Modern Web Interface**: Interactive chat UI with real-time responses
- ✅ **Azure Native**: Deploy to Azure App Service with one command using `azd`
- ✅ **Infrastructure as Code**: Bicep templates for reproducible deployments
- ✅ **Managed Identity**: Secure authentication to Azure AI Foundry
- ✅ **Application Insights**: Built-in monitoring and observability
- ✅ Interactive chat-based requirements gathering with adaptive questioning
- ✅ Microsoft Learn documentation integration for up-to-date Azure recommendations
- ✅ Automatic Bill of Materials (BOM) generation with SKU selection
- ✅ Real-time pricing using Azure Retail Prices API
- ✅ Professional Markdown proposal generation
- ✅ Sequential workflow orchestration (BOM → Pricing → Proposal)
- ✅ 20-turn conversation safety limit
- ✅ OpenTelemetry observability with Aspire Dashboard support

## Azure Resources

When deployed to Azure, the following resources are created:

| Resource | Purpose | SKU |
|----------|---------|-----|
| **App Service Plan** | Hosting compute | Configurable (default: B1) |
| **App Service** | Web application host | Python 3.11 on Linux |
| **Application Insights** | Monitoring and telemetry | Standard |
| **Log Analytics Workspace** | Log aggregation | Pay-as-you-go |

**Estimated Monthly Cost**: Starting at ~$13/month (B1 tier) + usage-based monitoring costs

### Managed Identity

The App Service uses a System-Assigned Managed Identity for secure authentication to Azure AI Foundry. Ensure the managed identity has:
- **Reader** role on the Azure AI Foundry project
- **Cognitive Services User** role on the AI resource

## Troubleshooting

**Error: AZURE_AI_PROJECT_ENDPOINT not set**
- Copy `.env.example` to `.env` and configure your Azure AI Foundry endpoint

**Authentication errors**
- Run `az login` to authenticate with Azure CLI
- Verify you have access to the Azure AI Foundry project

**Import errors**
- Ensure virtual environment is activated
- Run `pip install -r requirements.txt`

**Async generator cleanup errors on shutdown**
- These are harmless warnings from the MCP client during program shutdown
- The application includes a custom exception handler to suppress these

**Pricing returns $0.00**
- The Azure Pricing MCP server may not have pricing data for all SKU/region combinations
- Verify the service name and SKU match Azure's naming conventions
- Ensure the Azure Pricing MCP server is running at `http://localhost:8080/mcp`

## Contributing

See `.github/copilot-instructions.md` for development guidelines and agent implementation rules.

## License

This project is licensed under the [MIT License](LICENSE).
