# Azure Pricing Assistant - Test Suite

This directory contains comprehensive unit, integration, and end-to-end tests for the Azure Pricing Assistant multi-agent application.

## Directory Structure

```
tests/
├── unit/                  # Fast unit tests (no external dependencies)
├── integration/           # Integration tests (require Azure credentials)
├── e2e/                   # End-to-end workflow tests
└── README.md              # This file
```

## Running Tests

### All Unit Tests (Fast - No External Dependencies Required)
```bash
pytest tests/unit/ -v
```

### All Integration Tests (Require Azure Credentials)
```bash
RUN_LIVE_PRICING_INTEGRATION=1 pytest tests/integration/ -v -s
```

### All E2E Tests (Require Azure + Azure Pricing MCP Server)
```bash
RUN_LIVE_E2E=1 pytest tests/e2e/ -v -s
```

### All Tests
```bash
RUN_LIVE_PRICING_INTEGRATION=1 RUN_LIVE_E2E=1 pytest tests/ -v -s
```

## Test Categories

### Unit Tests (`tests/unit/`)

Fast tests with no external dependencies. These test individual components in isolation.

**Files:**
- `test_architect_agent.py` - Architect Agent creation and configuration tests
- `test_orchestrator_completion.py` - Question completion parsing and turn limit enforcement
- `test_metrics.py` - Metrics configuration tests
- `test_trace_log_correlation.py` - Logging and tracing correlation tests
- `test_pricing_agent.py` - Pricing Agent JSON parsing and schema validation
- `test_proposal_agent.py` - Proposal structure and formatting tests
- `test_service_name_mapping.py` - Azure service name normalization tests
- `test_pricing_failure_handling.py` - Pricing fallback logic tests
- `test_proposal_pricing_links.py` - Proposal pricing link formatting tests

**Run:**
```bash
pytest tests/unit/ -v
```

**Expected time:** ~10 seconds

### Integration Tests (`tests/integration/`)

Tests requiring Azure credentials or external services. These test component interactions.

**Files:**
- `test_pricing_integration.py` - Live Pricing Agent tests (requires Azure + MCP server)
- `test_proposal_workflow_integration.py` - Proposal generation workflow tests
- `test_web_handlers.py` - Web API handler tests
- `test_proposals_endpoint.py` - Proposal endpoint tests
- `test_retrieve_proposals_workflow.py` - Proposal retrieval workflow tests
- `test_ui_error_handling.py` - UI error handling tests
- `test_proposal_storage.py` - Session storage tests

**Prerequisites:**
- `AZURE_AI_PROJECT_ENDPOINT` environment variable set
- `AZURE_AI_MODEL_DEPLOYMENT_NAME` environment variable set
- Azure credentials available (via `az login` or `DefaultAzureCredential`)
- Azure Pricing MCP server running (for pricing integration tests)

**Run:**
```bash
RUN_LIVE_PRICING_INTEGRATION=1 pytest tests/integration/ -v -s
```

**Expected time:** ~30-120 seconds per test

### End-to-End Tests (`tests/e2e/`)

Complete workflow tests covering the entire pipeline from requirements gathering to proposal generation.

**Files:**
- `test_end_to_end_workflow.py` - Full pipeline: Architect Agent → Pricing → Proposal

**Prerequisites:**
- All integration test prerequisites
- Azure Pricing MCP server running at `http://localhost:8080/mcp`
  - Set `AZURE_PRICING_MCP_URL` environment variable if running elsewhere

**Run:**
```bash
RUN_LIVE_E2E=1 pytest tests/e2e/ -v -s
```

**Expected time:** ~60-120 seconds per test

## Environment Setup for Live Tests

### 1. Install Dependencies
```bash
pip install -e .[dev]
```

### 2. Configure Azure Credentials
```bash
az login
# or
azd auth login
```

### 3. Set Environment Variables
Create a `.env` file in the workspace root:
```
AZURE_AI_PROJECT_ENDPOINT=https://your-project.region.ai.azure.com
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4-deployment-name
AZURE_PRICING_MCP_URL=http://localhost:8080/mcp
```

### 4. Start Azure Pricing MCP (for Integration/E2E tests)
In a separate terminal:
```bash
cd /path/to/AzurePricingMCP
python -m azure_pricing_mcp --transport http --host 127.0.0.1 --port 8080
```

## Schema Validation

All tests validate against PRD-defined schemas:

- **BOM Schema** (PRD Section 4.3):
  - Required: serviceName, sku, quantity, region, armRegionName, hours_per_month
  - Constraints: quantity > 0, hours_per_month 1-744

- **Pricing Schema** (PRD Section 4.3):
  - Required: items[], total_monthly, currency, pricing_date
  - Item fields: serviceName, sku, region, armRegionName, quantity, hours_per_month, unit_price, monthly_cost
  - Constraints: quantity > 0, hours_per_month 1-744, pricing_date ISO 8601 (YYYY-MM-DD)

- **Proposal Schema**:
  - Markdown format with sections: Executive Summary, Solution Architecture, Cost Breakdown, Total Cost Summary
  - Must include pricing data and service details

## Troubleshooting

### "Context not properly initialized"
**Cause:** Missing Azure credentials  
**Solution:** Run `az login` and ensure `AZURE_AI_PROJECT_ENDPOINT` is set

### "Failed to parse JSON from response"
**Cause:** Agent not returning valid JSON  
**Solution:** Check agent instructions in `src/agents/` and verify model is outputting correct format

### "Azure Pricing MCP connection refused"
**Cause:** Azure Pricing MCP server not running  
**Solution:** Start the server: `python -m azure_pricing_mcp --transport http --host 127.0.0.1 --port 8080`

## Contributing

When adding new tests:

1. Place tests in the appropriate directory:
   - `unit/` - Fast tests with no external dependencies
   - `integration/` - Tests requiring Azure credentials or external services
   - `e2e/` - Full pipeline tests
2. Follow existing naming convention: `test_[feature]_[scenario]`
3. Add docstrings explaining what is being tested
4. Validate against schemas defined in PRD
5. Include both happy path and error cases
6. Update this README with new test descriptions