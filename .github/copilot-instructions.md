# GitHub Copilot Instructions for Azure Seller Assistant

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
- **Question Agent**: Uses `ChatAgent` or `HandoffBuilder` with termination condition detecting "We are DONE!".
- **Processing Pipeline**: Uses `SequentialBuilder` for BOM -> Pricing -> Proposal agents.
- Follow the orchestration patterns defined in `specs/PRD.md`.

### 3. Data Schemas
- **BOM JSON**: Must match the schema defined in the PRD (Section 4.2).
- **Pricing Output**: Must match the schema defined in the PRD (Section 4.3).
- **Proposal**: Must follow the markdown structure defined in the PRD (Section 4.4).

### 4. API Integration
- Use Azure Retail Prices API endpoint: `https://prices.azure.com/api/retail/prices`
- Follow the API usage guidelines in `specs/PRD.md`.
- Handle errors gracefully (return 0.0 for missing pricing data).

### 5. Code Organization
```
src/
├── agents/
│   ├── question_agent.py
│   ├── bom_agent.py
│   ├── pricing_agent.py
│   └── proposal_agent.py
└── utils/
    └── pricing_api.py
```

### 6. Testing Requirements
- All agent changes must be tested end-to-end.
- Verify "We are DONE!" termination for Question Agent.
- Validate JSON schema compliance for BOM output.
- Test pricing API integration with real calls.
- Review proposal output quality against PRD standards.

## Common Tasks

### Creating/Modifying an Agent
1. Read the relevant agent section in `specs/PRD.md`.
2. Implement using `AzureAIAgentClient.create_agent()`.
3. Ensure instructions reflect the "Capabilities" and "Role" defined in the PRD.

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

## Questions or Uncertainties

If agent behavior is unclear:
1. Check `specs/PRD.md` - it is the source of truth.
2. If the PRD is ambiguous, ask for clarification before implementing.
