# Azure Pricing Assistant

AI-powered Azure pricing solution using Microsoft Agent Framework with multi-agent workflow for requirements gathering, BOM generation, pricing calculation, and proposal creation.

**🌐 Web Application**: Access through a modern web interface for interactive chat-based requirements gathering and proposal generation.

**☁️ Azure Deployment**: Designed to run on Azure App Service with full infrastructure as code using Azure Developer CLI (azd).

## 🚀 Quick Start

**Deploy to Azure in 5 minutes**: See **[QUICKSTART.md](QUICKSTART.md)** for rapid deployment instructions.

**Full deployment guide**: See **[DEPLOYMENT.md](DEPLOYMENT.md)** for comprehensive step-by-step instructions.

## Architecture

The solution uses a two-stage orchestration pattern:

1. **Discovery Stage**: Interactive chat with the Question Agent to gather requirements
2. **Processing Stage**: Sequential workflow executing BOM → Pricing → Proposal agents

### Agents

| Agent | Tools | Purpose |
|-------|-------|--------|
| **Question Agent** | Microsoft Learn MCP | Gathers requirements through adaptive Q&A (max 20 turns) |
| **BOM Agent** | Microsoft Learn MCP | Maps requirements to Azure services and SKUs |
| **Pricing Agent** | Azure Pricing MCP | Calculates real-time costs for each BOM item |
| **Proposal Agent** | None | Generates professional Markdown proposal |

## Prerequisites

### For Local Development
- Python 3.10 or higher
- Azure CLI installed and authenticated (`az login`)
- Azure AI Foundry project with deployed model (e.g., gpt-4o-mini)

### For Azure Deployment
- [Azure Developer CLI (azd)](https://aka.ms/install-azd) installed
- [Azure CLI](https://docs.microsoft.com/cli/azure/install-azure-cli) installed
- Azure subscription with appropriate permissions
- Azure AI Foundry project endpoint configured

## Quick Start (Azure Deployment)

Deploy the application to Azure in minutes:

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
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and set:
   - `AZURE_AI_PROJECT_ENDPOINT`: Your Azure AI Foundry project endpoint
   - `AZURE_AI_MODEL_DEPLOYMENT_NAME`: Your deployed model name (default: gpt-4o-mini)
   - `AZURE_PRICING_MCP_URL`: Azure Pricing MCP server URL (default: http://localhost:8080/sse)

5. **Authenticate with Azure**
   ```bash
   az login
   ```

6. **Optional - Start Aspire Dashboard for Observability**
   ```bash
   docker run --rm -it -p 18888:18888 -p 4317:18889 --name aspire-dashboard mcr.microsoft.com/dotnet/aspire-dashboard:latest
   ```
   Access the dashboard at http://localhost:18888 to view OpenTelemetry traces.

## Usage

### Web Application (Recommended)

Start the Flask web server:

```bash
python app.py
```

Open your browser to http://localhost:8000 to access the interactive web interface.

### CLI Application (Legacy)

Run the command-line version:

```bash
python main.py
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

We are DONE!

✅ Requirements gathering complete!

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
azure-pricing-assistant/
├── app.py                      # Flask web application entry point
├── main.py                     # CLI entry point (legacy)
├── templates/
│   └── index.html             # Web UI for chat interface
├── src/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── question_agent.py   # Interactive requirements gathering
│   │   ├── bom_agent.py        # Bill of Materials generation
│   │   ├── pricing_agent.py    # Cost calculation via Azure Pricing MCP
│   │   └── proposal_agent.py   # Professional proposal generation
├── infra/
│   ├── main.bicep             # Azure infrastructure definition
│   ├── resources.bicep        # Resource definitions
│   └── main.parameters.json   # Deployment parameters
├── specs/
│   └── PRD.md                 # Product Requirements Definition
├── tests/                     # Test files
├── azure.yaml                 # Azure Developer CLI configuration
├── startup.sh                 # App Service startup script
├── requirements.txt
├── .env.example
├── .dockerignore
├── .gitignore
└── README.md
```

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
- Ensure the Azure Pricing MCP server is running at `http://localhost:8080/sse`

## Contributing

See `.github/copilot-instructions.md` for development guidelines and agent implementation rules.

## License

[Your License]
