# GitHub Copilot Instructions for Azure Pricing Assistant

## Project Overview
The **Azure Pricing Assistant** is an AI-powered tool that automates Azure solution design and cost estimation. It uses a multi-agent architecture (Question → BOM → Pricing → Proposal) built on the Microsoft Agent Framework to gather requirements, generate Bills of Materials, calculate real-time pricing, and create professional proposals.

**Tech Stack**: Python 3.10+, Microsoft Agent Framework, Azure AI Foundry, Azure Pricing MCP, OpenTelemetry

## Purpose
Keep Copilot completions aligned with the PRD, schemas, orchestration rules, and local/dev workflows for the Azure Pricing Assistant multi-agent app.

## Required Reading
- specs/PRD.md is the single source of truth for roles, prompts, orchestration, tools, schemas, and error handling. Read it before changing agents or instructions.

## Fast Start (local/dev)
- Install deps: `pip install -e .[dev]` (Python 3.10+).
- Env vars (see README table): AZURE_AI_PROJECT_ENDPOINT (required), AZURE_PRICING_MCP_URL (default http://localhost:8080/mcp), FLASK_SECRET_KEY for web, optional PORT.
- Azure auth: `az login` (and `azd auth login` for azd flows).
- Start Azure Pricing MCP: run the server from https://github.com/nabeelp/AzurePricingMCP/tree/streamable-http and keep endpoint in sync with AZURE_PRICING_MCP_URL.
- Quick-start Azure Pricing MCP (per repo README; adjust if updated):
	- `git clone https://github.com/nabeelp/AzurePricingMCP && cd AzurePricingMCP && git checkout streamable-http`
	- `python -m venv .venv && source .venv/bin/activate` (or `.venv\Scripts\activate` on Windows)
	- `pip install -r requirements.txt`
	- `python -m azure_pricing_mcp --transport http --host 127.0.0.1 --port 8080`; default HTTP endpoint http://localhost:8080/mcp
	- Export/override `AZURE_PRICING_MCP_URL` in this app to point at the running endpoint
- Run web app: `python -m src.web.app`. CLI: `python -m src.cli.app`.
- Tests: `pytest tests/test_bom_agent.py tests/test_pricing_agent.py tests/test_bom_integration.py` (add more cases as you add features).

## Agent & Orchestration Rules
- Follow PRD Section 5.2: discovery via ChatAgent loop, then SequentialBuilder BOM → Pricing → Proposal. Keep this order unchanged.
- Completion contract: Question Agent final message is a JSON object `{ "requirements": "...", "done": true }` in a ```json code block; use this flag to trigger BOM/Pricing/Proposal. Do not emit legacy phrases or extra prose in the final message.
- 20-turn max for discovery. Keep prompts aligned to the role/capability definitions in PRD Section 4.

## Tooling (authoritative list in PRD Section 4.3)
- Microsoft Learn MCP (`microsoft_docs_search`) for capability/region checks.
- Azure Pricing MCP (SSE): azure_cost_estimate, azure_price_search, azure_price_compare, azure_region_recommend, azure_discover_skus, azure_sku_discovery, get_customer_discount. Use AZURE_PRICING_MCP_URL (default http://localhost:8080/mcp).
- Choose tools based on need (search → discover → estimate). Retry or fall back to $0.00 with an error note on failures.

## Data Schemas (PRD Sections 4.2–4.4)
- BOM: array of `{ serviceName, sku, quantity, region, armRegionName, hours_per_month }`.
- Pricing output: `{ items[], total_monthly, currency, pricing_date, savings_options?, errors? }` where each item has `{ serviceName, sku, region, armRegionName, quantity, hours_per_month, unit_price, monthly_cost, notes? }`. Sum monthly_cost * quantity into total_monthly. On lookup failure, set price to 0 and record an error note.
- Proposal structure: Executive Summary, Solution Architecture, Cost Breakdown, Total Cost Summary, Next Steps, Assumptions. Keep Markdown output clean and client-ready.

## Coding Standards
- Formatting: black (line length 100). Typing: add type hints; mypy config lives in pyproject (not fully strict—respect current settings).
- Async-first: agent framework APIs are async; avoid blocking calls and ensure awaits.
- Error handling: wrap external calls (MCP/HTTP/JSON parsing) with clear fallbacks and notes.
- Logging/tracing: use src/shared/logging.py setup; include trace/span ids automatically. Prefer structured, informative messages at INFO/ERROR.
- Avoid introducing new frameworks/libraries without PRD/owner approval.

### Observability defaults
- OTLP endpoint: set `OTLP_ENDPOINT` or `OTEL_EXPORTER_OTLP_ENDPOINT` (e.g., `http://localhost:4317`).
- OTLP headers: set `OTLP_HEADERS` or `OTEL_EXPORTER_OTLP_HEADERS` for auth (e.g., `Authorization=Bearer <token>`).
- Insecure transport allowed when endpoint is http:// (see src/shared/logging.py); use https in shared environments.

## Testing Expectations
- Cover end-to-end flow: discovery termination phrase detection, BOM schema validity, pricing with MCP (and fallback), proposal formatting.
- Add/adjust tests when changing schemas, prompts, or orchestration. Keep integration tests passing with live or mocked MCP as appropriate.

## Security & Data Handling
- Do not log secrets or raw customer-sensitive content. Keep env vars in .env, not in code or prompts.
- Sanitize tool inputs; avoid echoing credentials in responses.

## Update Discipline
- Requirement changes flow: update specs/PRD.md first, then instructions, then code/tests to stay in lockstep.

## Common Pitfalls
- Forgetting to start or point to the Azure Pricing MCP server.
- Letting the Question Agent emit prose or a legacy phrase instead of the `{ "done": true }` JSON envelope.
- Drifting from schemas (missing armRegionName, wrong totals, missing pricing_date/currency).
- Not awaiting async tool calls or handling tool failures with $0.00 + error notes.

## Project Structure
```
azure-pricing-assistant/
├── src/
│   ├── agents/           # AI agents (question, bom, pricing, proposal)
│   ├── core/             # Orchestration, config, session management
│   ├── interfaces/       # Abstract base classes & handlers
│   ├── web/              # Flask web application
│   ├── cli/              # Command-line interface
│   └── shared/           # Logging, errors, utilities
├── tests/                # Unit, integration, and E2E tests
├── specs/                # PRD.md (requirements document)
├── infra/                # Azure Bicep templates for deployment
├── .github/              # This file and CI configuration
└── pyproject.toml        # Python project metadata
```

## Build, Test, and Lint Commands
All commands should be run from the repository root:

### Installation
```bash
# Development (recommended - includes all dependencies)
pip install -e .[dev]

# Web interface only
pip install -e .[web]

# CLI interface only
pip install -e .[cli]
```

### Testing
```bash
# Unit tests only (no Azure credentials required)
pytest tests/ -k "not integration and not e2e" -v

# Run specific test file
pytest tests/test_bom_agent.py -v

# BOM integration tests (requires Azure credentials)
RUN_LIVE_BOM_INTEGRATION=1 pytest tests/test_bom_integration.py -v -s

# Full E2E tests (requires Azure credentials + Azure Pricing MCP server)
RUN_LIVE_E2E=1 pytest tests/test_end_to_end_workflow.py -v -s

# All tests with coverage
pytest tests/ --cov=src --cov-report=html -v
```

### Linting and Formatting
```bash
# Format code with black (line length 100)
black src/ tests/ --line-length 100

# Type checking with mypy
mypy src/

# Check formatting without changing files
black src/ tests/ --check --line-length 100
```

### Running the Application
```bash
# Web interface (default: http://localhost:8000)
python -m src.web.app

# CLI interface
python -m src.cli.app
```

## Required Environment Variables
Create a `.env` file (copy from `.env.example`):

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `AZURE_AI_PROJECT_ENDPOINT` | Yes | — | Azure AI Foundry project endpoint |
| `AZURE_PRICING_MCP_URL` | No | http://localhost:8080/mcp | Azure Pricing MCP server endpoint |
| `FLASK_SECRET_KEY` | Yes (web) | — | Flask session secret key |
| `PORT` | No | 8000 | Local web server port |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | No | gpt-4o-mini | Azure AI model deployment |

## Contributing Guidelines
1. **Read specs/PRD.md first** - This is the authoritative source for requirements, schemas, and agent behavior
2. **Follow existing patterns** - Match coding style, structure, and conventions in the codebase
3. **Add tests** - All new features require unit tests; integration tests when interacting with external services
4. **Update schemas** - If changing data structures, update PRD first, then code, then tests
5. **Run tests before PR** - Ensure all unit tests pass before submitting changes
6. **Format code** - Run `black` before committing (line length 100)
7. **Document changes** - Update relevant README or documentation files
8. **Keep changes minimal** - Make surgical, focused changes; avoid unnecessary refactoring
