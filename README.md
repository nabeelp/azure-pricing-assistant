# Azure Seller Assistant

AI-powered Azure pricing solution using Microsoft Agent Framework with multi-agent workflow for requirements gathering, BOM generation, pricing calculation, and proposal creation.

## Project Status

**Current Phase**: Phase 1 - Mock Implementation

Phase 1 focuses on establishing workflow orchestration patterns with hardcoded responses to validate the multi-agent architecture.

## Architecture

- **Question Agent**: Interactive chat using ChatAgent with thread-based conversation (max 10 turns)
- **BOM Agent**: Bill of Materials generation
- **Pricing Agent**: Cost calculation
- **Proposal Agent**: Professional proposal generation

Workflow: Question Agent (chat) → Sequential workflow (BOM → Pricing → Proposal)

## Prerequisites

- Python 3.10 or higher
- Azure CLI installed and authenticated (`az login`)
- Azure AI Foundry project with deployed model (e.g., gpt-4o-mini)

## Setup

1. **Clone repository**
   ```bash
   git clone <repository-url>
   cd azure-seller-assistant
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
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

5. **Authenticate with Azure**
   ```bash
   az login
   ```

## Usage

Run the Phase 1 implementation:

```bash
python main.py
```

The application will:
1. Ask you questions about your Azure requirements
2. Gather workload type and region information
3. Automatically generate BOM, pricing, and proposal (using mock data)
4. Display the final proposal

### Example Interaction

```
Agent: Hello! I'll help you price an Azure solution. Let's start!
Agent: What type of workload will you run on Azure?
You: Web application

Agent: Which Azure region would you like to deploy to?
You: East US

Agent: Summary of requirements:
- Workload: Web application
- Region: East US

We are DONE!

✅ Requirements gathering complete!

[Sequential workflow processes BOM → Pricing → Proposal]

=== Final Proposal ===
Azure Solution Proposal

Executive Summary:
Based on your requirements for a web application in East US...

Cost Breakdown:
- Virtual Machines (Standard_D2s_v3, 2 instances): $100.00/month

Total Monthly Cost: $100.00
Total Annual Cost: $1,200.00
```

## Project Structure

```
azure-seller-assistant/
├── src/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── question_agent.py
│   │   ├── bom_agent.py
│   │   ├── pricing_agent.py
│   │   └── proposal_agent.py
│   └── utils/
│       └── __init__.py
├── specs/
│   ├── phase1/              # Phase 1 specifications
│   ├── phase2/              # Phase 2 specifications
│   └── shared/              # Shared resources (API specs)
├── main.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Documentation

- **Phase 1 Architecture**: `specs/phase1/ARCHITECTURE.md`
- **Phase 1 Agent Instructions**: `specs/phase1/AGENT_INSTRUCTIONS.md`
- **Phase 1 Progress**: `specs/phase1/PROGRESS.md`
- **API Specifications**: `specs/shared/API_SPEC.md`
- **GitHub Copilot Instructions**: `.github/copilot-instructions.md`

## Phase 1 Goals

- ✅ Validate ChatAgent thread-based conversation with "We are DONE!" termination
- ✅ Test sequential workflow execution (BOM → Pricing → Proposal)
- ✅ Implement 10-turn safety limit for interactive chat
- ✅ Establish hybrid orchestration pattern (chat + workflow)

## Next Steps (Phase 2)

Phase 2 will enhance the solution with:
- Intelligent question sequencing based on workload type
- Real Azure Retail Prices API integration
- Dynamic SKU selection and BOM generation
- Professional proposal formatting

See `specs/phase2/` for Phase 2 specifications.

## Troubleshooting

**Error: AZURE_AI_PROJECT_ENDPOINT not set**
- Copy `.env.example` to `.env` and configure your Azure AI Foundry endpoint

**Authentication errors**
- Run `az login` to authenticate with Azure CLI
- Verify you have access to the Azure AI Foundry project

**Import errors**
- Ensure virtual environment is activated
- Run `pip install -r requirements.txt`

## Contributing

See `.github/copilot-instructions.md` for development guidelines and agent implementation rules.

## License

[Your License]
