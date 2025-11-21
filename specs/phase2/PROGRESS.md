# Phase 2 Implementation Progress

## Goal
Replace mock responses with intelligent prompt engineering, add Azure Retail Prices API integration as external tool, implement JSON parsing for BOM, and enhance proposal generation with pay-as-you-go pricing.

---

## Tasks

### ✅ Task 2.1: Enhance Question Agent with Smart Prompting

**Note**: Question Agent uses `ChatAgent.run_stream()` with thread (not HandoffBuilder workflow)

- [ ] Update `question_agent.py` with Phase 2 instructions from `specs/phase2/AGENT_INSTRUCTIONS.md`
- [ ] Copy enhanced instructions EXACTLY (do not paraphrase)
- [ ] Maintain ChatAgent pattern with thread-based conversation (max 10 turns)
- [ ] Verify instruction includes intelligent question flow:
  - [ ] First: Workload type (web, database, analytics, ML, etc.)
  - [ ] Second: Scale requirements (users, requests, data volume)
  - [ ] Third: Specific Azure services or recommendations
  - [ ] Fourth: Deployment region
  - [ ] Optional: Special requirements (HA, compliance)
- [ ] Ensure minimum completion criteria documented:
  - [ ] Workload type + at least one service + region
- [ ] Verify "We are DONE!" instruction preserved
- [ ] Test with various workload scenarios:
  - [ ] Web application
  - [ ] Database workload
  - [ ] Analytics workload
  - [ ] Multi-service scenario

---

### ✅ Task 2.2: Build BOM Agent with JSON Parsing

- [ ] Update `bom_agent.py` with Phase 2 instructions from `specs/phase2/AGENT_INSTRUCTIONS.md`
- [ ] Copy JSON schema template exactly
- [ ] Verify service-to-SKU mapping guidance included
- [ ] Verify default `hours_per_month: 730` instruction
- [ ] Implement JSON extraction logic:
  - [ ] Handle markdown code blocks (```json ... ```)
  - [ ] Parse JSON array with `json.loads()`
  - [ ] Validate required fields:
    - [ ] serviceName
    - [ ] sku
    - [ ] quantity
    - [ ] region
    - [ ] armRegionName
    - [ ] hours_per_month
- [ ] Add error handling:
  - [ ] Invalid JSON → log error, request retry
  - [ ] Missing fields → validation error
  - [ ] Malformed structure → graceful failure
- [ ] Test with various requirement scenarios:
  - [ ] Simple web app → App Service
  - [ ] Database → SQL Database
  - [ ] Multi-service → App Service + SQL + Storage

---

### ✅ Task 2.3: Create Azure Pricing API Tool

- [ ] Create `src/utils/pricing_api.py`
- [ ] Implement `get_azure_price(service_name: str, sku_name: str, region: str) -> float`:
  - [ ] Import `requests` library
  - [ ] Define endpoint: `https://prices.azure.com/api/retail/prices`
  - [ ] Construct OData filter:
    ```python
    f"serviceName eq '{service}' and skuName eq '{sku}' and armRegionName eq '{region}'"
    ```
  - [ ] Make HTTP GET request with params
  - [ ] Parse JSON response
  - [ ] Extract `retailPrice` from `Items[0]`
  - [ ] Return price as float
- [ ] Add comprehensive error handling:
  - [ ] No results found → return 0.0, log warning
  - [ ] HTTP timeout → retry once with exponential backoff
  - [ ] Invalid response → return 0.0, log error
  - [ ] API error codes (400, 429, 500) → handle appropriately
- [ ] Test with real API calls:
  - [ ] Virtual Machines / Standard_D2s_v3 / eastus
  - [ ] Azure App Service / P1v2 / eastus
  - [ ] SQL Database / S1 / eastus
- [ ] Document API response format in docstring

---

### ✅ Task 2.4: Implement Pricing Agent with Tool Calling

- [ ] Update `pricing_agent.py` with Phase 2 instructions from `specs/phase2/AGENT_INSTRUCTIONS.md`
- [ ] Import `get_azure_price` from `src.utils.pricing_api`
- [ ] Register as FunctionTool:
  ```python
  from agent_framework import FunctionTool
  
  pricing_tool = FunctionTool(
      name="get_azure_price",
      description="Get Azure retail pricing",
      func=get_azure_price
  )
  ```
- [ ] Add tool to agent creation:
  ```python
  pricing_agent = await client.create_agent(
      name="pricing_agent",
      instructions="...",
      tools=[pricing_tool]
  )
  ```
- [ ] Verify instructions include:
  - [ ] Parse BOM JSON from previous agent
  - [ ] Call get_azure_price for each item
  - [ ] Calculate: monthly_cost = retailPrice × quantity × hours_per_month
  - [ ] Sum all costs for total
  - [ ] Format as JSON output
- [ ] Test tool calling:
  - [ ] Verify agent calls tool correctly
  - [ ] Check calculations are accurate
  - [ ] Validate JSON output format
- [ ] Test error scenarios:
  - [ ] API returns 0.0 → verify note added
  - [ ] Invalid BOM JSON → verify graceful handling

---

### ✅ Task 2.5: Enhance Proposal Agent Document Generation

- [ ] Update `proposal_agent.py` with Phase 2 instructions from `specs/phase2/AGENT_INSTRUCTIONS.md`
- [ ] Copy template structure exactly
- [ ] Verify all required sections included:
  - [ ] Executive Summary (2-3 paragraphs)
  - [ ] Solution Architecture (service list)
  - [ ] Cost Breakdown (markdown table)
  - [ ] Total Cost Summary (monthly + annual)
  - [ ] Next Steps (deployment recommendations)
  - [ ] Assumptions (operating hours, region, pricing)
- [ ] Verify markdown formatting requirements:
  - [ ] Proper headers (# ## ###)
  - [ ] Tables for cost breakdown
  - [ ] Bullet points for lists
- [ ] Test proposal generation:
  - [ ] Simple single-service solution
  - [ ] Multi-service solution
  - [ ] Verify all data included from conversation
- [ ] Validate professional tone and completeness
- [ ] Check client-ready quality

---

### ✅ Task 2.6: End-to-End Integration Testing

- [ ] Configure environment:
  - [ ] Create `.env` with Azure AI Foundry credentials
  - [ ] Run `az login` to authenticate
  - [ ] Verify AZURE_AI_PROJECT_ENDPOINT set
  - [ ] Verify AZURE_AI_MODEL_DEPLOYMENT_NAME set
- [ ] **Test Scenario 1: Simple Web Application**
  - [ ] Start: "I need help pricing a web app"
  - [ ] Verify Question Agent asks intelligent questions
  - [ ] Provide: "10,000 users per day, East US region"
  - [ ] Confirm "We are DONE!" terminates properly
  - [ ] Validate BOM JSON:
    - [ ] Contains Azure App Service
    - [ ] Appropriate SKU selected (Standard or Premium)
    - [ ] Correct region mapping
  - [ ] Check Pricing Agent:
    - [ ] Calls real Azure Retail Prices API
    - [ ] Returns valid pricing data
    - [ ] Calculations correct
  - [ ] Review final proposal:
    - [ ] All sections present
    - [ ] Professional formatting
    - [ ] Accurate cost data
- [ ] **Test Scenario 2: Database Workload**
  - [ ] Start: "I need a database solution"
  - [ ] Verify adaptive questioning
  - [ ] Validate SQL Database or Cosmos DB selected
  - [ ] Check pricing accuracy
- [ ] **Test Scenario 3: Multi-Service Solution**
  - [ ] Start: "Web app with database and storage"
  - [ ] Verify BOM includes all 3 services
  - [ ] Check pricing for each service
  - [ ] Validate total cost calculation
- [ ] **Test Edge Cases**:
  - [ ] Unknown SKU → verify fallback pricing ($0 with note)
  - [ ] Invalid region → verify error handling
  - [ ] API timeout → verify retry logic works
  - [ ] API returns empty results → verify $0 fallback
- [ ] Document test results:
  - [ ] Create example outputs for each scenario
  - [ ] Note any issues or unexpected behavior
  - [ ] Record API response times
  - [ ] Document pricing accuracy

---

## Known Issues
None yet

---

## Success Criteria
- ✅ Question Agent adapts intelligently to workload type
- ✅ BOM Agent produces valid, appropriate SKU selections
- ✅ Pricing Agent successfully calls Azure Retail Prices API
- ✅ Calculations are mathematically correct
- ✅ Proposal is professional and client-ready
- ✅ Error handling works gracefully for API failures
- ✅ All JSON parsing works correctly

---

## Timeline
**Target**: Complete within 2-3 days

---

## Next Steps After Completion
1. Comprehensive error handling audit
2. Add logging and observability
3. Consider checkpointing for long conversations
4. Explore reserved instance pricing support
5. Add unit tests for critical components
6. Performance optimization
7. Documentation updates
