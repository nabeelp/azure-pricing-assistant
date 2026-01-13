# Azure Pricing Assistant - Test Suite

This directory contains comprehensive unit, integration, and end-to-end tests for the Azure Pricing Assistant multi-agent application.

## Test Files Overview

### Unit Tests

#### `test_bom_agent.py` (24 tests)
Tests for Bill of Materials Agent JSON parsing and schema validation.

- **TestJSONExtraction** (5 tests): Validates JSON extraction from various markdown/text formats
- **TestBOMValidation** (10 tests): Validates BOM schema (required fields, types, value ranges)
- **TestEndToEndParsing** (4 tests): End-to-end parsing workflows

**Run:**
```bash
pytest tests/test_bom_agent.py -v
```

#### `test_pricing_agent.py` (18 tests)
Tests for Pricing Agent JSON parsing and schema validation.

- **TestJSONExtraction** (3 tests): JSON extraction from code blocks and raw text
- **TestPricingValidation** (10 tests): Pricing schema validation (fields, types, dates, ranges)
- **TestEndToEndParsing** (5 tests): End-to-end pricing workflows with errors and savings options

**Run:**
```bash
pytest tests/test_pricing_agent.py -v
```

#### `test_orchestrator_completion.py` (9 tests)
Tests for Question Agent completion detection and turn limit enforcement.

- **Completion Parsing** (3 tests): JSON payload detection from agent responses
- **Turn Limit** (3 tests): Session turn counter behavior and limits
- **Code Block Extraction** (3 tests): Strict ```json code block extraction

**Run:**
```bash
pytest tests/test_orchestrator_completion.py -v
```

### Integration Tests

#### `test_bom_integration.py`
Live agent tests requiring Azure AI project credentials. Tests BOM Agent with real Azure models.

**Prerequisites:**
- `AZURE_AI_PROJECT_ENDPOINT` environment variable set
- `AZURE_AI_MODEL_DEPLOYMENT_NAME` environment variable set
- Azure credentials available (via `az login` or `DefaultAzureCredential`)

**Run:**
```bash
RUN_LIVE_BOM_INTEGRATION=1 pytest tests/test_bom_integration.py -v -s
```

**Test Scenarios:**
1. Simple Web Application (App Service)
2. Database Workload (SQL Database)
3. Multi-Service Solution (App Service + SQL + Storage)

#### `test_pricing_integration.py`
Live Pricing Agent tests requiring Azure AI project credentials and Azure Pricing MCP server.

**Prerequisites:**
- `AZURE_AI_PROJECT_ENDPOINT` environment variable set
- `AZURE_AI_MODEL_DEPLOYMENT_NAME` environment variable set
- Azure credentials available (via `az login` or `DefaultAzureCredential`)
- Azure Pricing MCP server running at `http://localhost:8080/mcp`
  - Set `AZURE_PRICING_MCP_URL` environment variable if running elsewhere

**Run:**
```bash
RUN_LIVE_PRICING_INTEGRATION=1 pytest tests/test_pricing_integration.py -v -s
```

**Test Scenarios:**
1. Simple App Service pricing lookup
2. Multiple services pricing with total calculation
3. Graceful fallback for unavailable pricing ($0.00 with error notes)
4. Total calculation accuracy validation
5. Region-specific pricing variations

### End-to-End Tests

#### `test_end_to_end_workflow.py`
Complete workflow tests: Question Agent → BOM Agent → Pricing Agent → Proposal Agent

Tests the full pipeline with schema validation at each step.

**Prerequisites:**
- All integration test prerequisites (Azure credentials, environment variables)
- Azure Pricing MCP server running at `http://localhost:8080/mcp` (for pricing)
  - Set `AZURE_PRICING_MCP_URL` environment variable if running elsewhere

**Run:**
```bash
RUN_LIVE_E2E=1 pytest tests/test_end_to_end_workflow.py -v -s
```

**Test Scenarios:**
1. Simple Web Application (Question → BOM → Pricing → Proposal)
2. Database Workload (Question → BOM → Pricing → Proposal)

## Running All Tests

### Unit Tests Only (No Live Agents Required)
```bash
pytest tests/ -k "not integration and not e2e" -v
```

### Unit + BOM Integration
```bash
pytest tests/ -k "not e2e" -v
RUN_LIVE_BOM_INTEGRATION=1 pytest tests/test_bom_integration.py -v -s
```

### All Tests (Full Suite)
```bash
RUN_LIVE_BOM_INTEGRATION=1 RUN_LIVE_E2E=1 pytest tests/ -v -s
```

### With Coverage Report
```bash
pytest tests/ --cov=src --cov-report=html -v
```

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

### 4. Start Azure Pricing MCP (for E2E tests)
In a separate terminal:
```bash
cd /path/to/AzurePricingMCP
python -m azure_pricing_mcp --transport http --host 127.0.0.1 --port 8080
```

## Test Results & Timing

### Expected Timing

**Unit Tests** (~10 seconds)
- BOM Agent: 2-3s
- Pricing Agent: 2-3s
- Orchestrator: 2-3s

**BOM Integration** (~30-60 seconds per test)
- Simple Web App: 30s
- Database Workload: 30s
- Multi-Service: 30s

**E2E Tests** (~60-120 seconds per test)
- Simple Web App: 90-120s (includes pricing lookups)
- Database Workload: 90-120s

### Expected Output

**Successful unit test:**
```
tests/test_pricing_agent.py::TestJSONExtraction::test_extract_from_markdown_json_block PASSED [100%]
================================================ 1 passed in 2.30s ==================================================
```

**Successful integration test:**
```
=== Test 1: Simple Web Application ===

Requirements:
Workload Type: Web application
...

BOM Agent Response:
[JSON output from agent]

✅ Successfully parsed BOM with 2 items:
  Service: Azure App Service
  SKU: P1V2
  ...

✅ Test passed!
```

**Successful E2E test:**
```
PHASE 1: Question Agent - Gathering Requirements
-----------...
✅ Requirements gathered: Workload: web app...

PHASE 2: BOM Agent - Generating Bill of Materials
-----------...
✅ BOM schema valid: 2 services

PHASE 3: Pricing Agent - Calculating Costs
-----------...
✅ Pricing schema valid:
  - Items: 2
  - Total Monthly: $1234.56

PHASE 4: Proposal Agent - Generating Proposal
-----------...
✅ Proposal generated successfully

✅ E2E TEST PASSED
```

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

### "SyntaxError in pricing_agent.py"
**Cause:** Agent instructions string not properly closed
**Solution:** Check `src/agents/pricing_agent.py` line 200+ for unterminated triple-quoted strings

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

## Contributing

When adding new tests:

1. Follow existing naming convention: `test_[feature]_[scenario]`
2. Add docstrings explaining what is being tested
3. Validate against schemas defined in PRD
4. Include both happy path and error cases
5. Update this README with new test descriptions

