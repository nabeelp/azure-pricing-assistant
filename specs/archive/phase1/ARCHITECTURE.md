# Phase 1 Architecture - Mock Implementation

## Overview
Phase 1 establishes the basic multi-agent workflow structure using hardcoded mock responses. The goal is to validate orchestration patterns and event handling without API complexity.

## Technology Stack
- **Framework**: Microsoft Agent Framework (`agent-framework-azure-ai`)
- **AI Service**: Azure AI Foundry Agent Service
- **Authentication**: Azure CLI credentials
- **Language**: Python 3.10+

## High-Level Flow
```
User Input → Question Agent (Handoff Workflow)
           ↓
      "We are DONE!" detected
           ↓
Requirements Summary → Sequential Workflow:
  1. BOM Agent → Mock JSON
  2. Pricing Agent → Mock Costs
  3. Proposal Agent → Simple Proposal
           ↓
Final Proposal Output
```

## Agent Specifications

### 1. Question Agent (Interactive Chat)
**Orchestration**: Direct ChatAgent.run_stream() with thread-based conversation

**Instructions**: Ask 1-2 simple questions about workload and region, then output "We are DONE!"

**Termination**: Text detection of "We are DONE!" in agent responses (max 10 turns)
```python
if "We are DONE!" in last_response:
    requirements_summary = last_response
    break
```

**Mock Behavior**: 
- Greeting: "Hello! I'll help you price an Azure solution."
- Question 1: "What type of workload?"
- Question 2: "What region?"
- Output: Simple summary + "We are DONE!"

### 2. BOM Agent (Sequential - Stage 1)
**Instructions**: Return hardcoded JSON array

**Mock Output**:
```json
[
  {
    "serviceName": "Virtual Machines",
    "sku": "Standard_D2s_v3",
    "quantity": 2,
    "region": "East US",
    "armRegionName": "eastus",
    "hours_per_month": 730
  }
]
```

### 3. Pricing Agent (Sequential - Stage 2)
**Instructions**: Return hardcoded pricing data

**Mock Output**:
```json
{
  "items": [
    {
      "service": "Virtual Machines",
      "sku": "Standard_D2s_v3",
      "monthly_cost": 100.00
    }
  ],
  "total_monthly": 100.00
}
```

### 4. Proposal Agent (Sequential - Stage 3)
**Instructions**: Create simple text proposal

**Mock Output**:
```
Azure Solution Proposal

Executive Summary:
[Brief description]

Cost Breakdown:
- Virtual Machines: $100/month

Total Monthly Cost: $100
Total Annual Cost: $1,200
```

## Workflow Orchestration

### Question Agent (Direct ChatAgent)
```python
# Create agent and conversation thread
question_agent = create_question_agent(client)
thread = question_agent.get_new_thread()

# Initial greeting
async for update in question_agent.run_stream("Hello! Let's start!", thread=thread):
    if update.text:
        print(update.text, end='', flush=True)

# Interactive loop (max 10 turns)
for turn in range(10):
    user_input = input("You: ")
    last_response = ""
    
    async for update in question_agent.run_stream(user_input, thread=thread):
        if update.text:
            print(update.text, end='', flush=True)
            last_response += update.text
    
    if "We are DONE!" in last_response:
        requirements_summary = last_response
        break
```

### Sequential Workflow
```python
from agentStreaming Pattern
**Question Agent** (ChatAgent streaming):
```python
async for update in question_agent.run_stream(user_input, thread=thread):
    if update.text:
        print(update.text, end='', flush=True)
        last_response += update.text
```

**Sequential Workflow** (Workflow events):
```python
async for event in workflow.run_stream(requirements):
    if isinstance(event, AgentRunUpdateEvent):
        print(event.data, end='', flush=True)
    elif isinstance(event, WorkflowOutputEvent):
        final_proposal = event.data
async for event in workflow.run_stream(initial_message):
    if isinstance(event, RequestInfoEvent):
        # Prompt user for input
        user_input = input("You: ")
        async for response in workflow.send_responses_streaming({event.request_id: user_input}):
            # Handle response events
            pass
    elif isinstance(event, WorkflowCompletedEvent):
        # Extract final result
        break
```

## File Structure
```
src/
├── agents/
│   ├── __init__.py
│   ├── question_agent.py
│   ├── bom_agent.py
│   ├── pricing_agent.py
│   └── proposal_agent.py
main.py
requirements.txt
.env.example
```

## Configuration

### Environment Variables
```
AZURE_AI_PROJECT_ENDPOINT=https://<project>.services.ai.azure.com/api/projects/<project-id>
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o-mini
```

### Setup Steps
1. Create Azure AI Foundry project
2. Deploy GPT-4o-mini or similar model
3. Run `az login` for authentication
4. Create `.env` file with project endpoint

## Success Criteria
- ✅ Question Agent asks questions and detects "We are DONE!"
- ✅ Handoff workflow terminates correctly
- ✅ Sequential workflow executes all 3 agents in order
- ✅ Final proposal contains mock data
- ✅ Event loop handles RequestInfoEvent and WorkflowCompletedEvent

## Testing Strategy
1. Verify Question Agent conversation flow
2. Test "We are DONE!" termination detection
3. Validate handoff → sequential transition
4. Check each agent executes in correct order
5. Verify final proposal contains expected mock content

## No External Dependencies
- No Azure Retail Prices API integration
- No JSON parsing complexity
- No error handling for API failures
- Focus purely on workflow orchestration
