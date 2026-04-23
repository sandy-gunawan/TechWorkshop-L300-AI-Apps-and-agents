# Implementation Guide

A step-by-step walkthrough for building each agent pattern. Start with Part A (infrastructure), then pick the pattern you want to learn.

---

## Part A: Foundation — Azure Resources & Environment

### Step 1: Deploy Azure Resources

The Bicep template deploys everything you need:

```powershell
az deployment group create \
  --resource-group rg-aiappsagent-shopassist \
  --template-file src/infra/DeployAzureResources.bicep \
  --parameters objectId=$(az ad signed-in-user show --query id -o tsv)
```

This creates: Cosmos DB, AI Foundry + Project, Storage Account, Container Registry, Container Apps, Application Insights, Log Analytics.

### Step 2: Configure Environment Variables

Copy `src/env_sample.txt` to `src/.env` and fill in values from your deployed resources:

| Variable | Where to find it |
|----------|-----------------|
| `FOUNDRY_ENDPOINT` | Azure Portal → AI Foundry → Project → Overview → Endpoint |
| `gpt_endpoint` | Azure Portal → AI Services → Keys and Endpoint |
| `COSMOS_ENDPOINT` | Azure Portal → Cosmos DB → Keys → URI |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Azure Portal → Application Insights → Overview |
| `storage_account_name` | Azure Portal → Storage Account → Overview |

### Step 3: Load Product Data

```powershell
cd src
python pipelines/ingest_to_cosmos.py
```

This loads 54 products from `data/product_catalog.json` into Cosmos DB with vector embeddings.

---

## Part B: Single Agent — The Simplest Starting Point

**Goal**: Understand how a basic agent works before adding complexity.

**File**: [src/app/tools/singleAgentExample.py](../../src/app/tools/singleAgentExample.py)

### What It Does

1. Creates a raw Azure OpenAI client
2. Sends the user message with a system prompt
3. Returns the response

### Key Code

```python
from openai import AzureOpenAI

client = AzureOpenAI(azure_endpoint=endpoint, ...)

response = client.chat.completions.create(
    model=deployment_name,
    messages=[
        {"role": "system", "content": "You are a helpful assistant..."},
        {"role": "user", "content": user_message}
    ]
)
return response.choices[0].message.content
```

### To Enable It

In `chat_app.py`, uncomment the import and the call:

```python
from handlers.single_agent_handler import handle_single_agent
# ...
await handle_single_agent(websocket, user_message, persistent_cart)
```

---

## Part C: Multi-Agent with Foundry

**Goal**: Build a production-grade multi-agent system with intent routing, specialized agents, and MCP tools.

### Step 1: Write Agent Prompts

Each agent has a prompt file in `src/prompts/`. A good agent prompt:

- Defines the agent's **role** clearly
- Specifies **output format** (JSON structure)
- Lists **what tools to use** and when
- Includes **guardrails** (what NOT to do)

Example from `ShopperAgentPrompt.txt`:
```
You are the public facing assistant of Zava...
You MUST respond in valid JSON with keys: answer, image_output, products
```

### Step 2: Register Agents in Foundry

Each agent has an initializer script. Run them to register agents in Foundry:

```powershell
python app/agents/shopperAgent_initializer.py
python app/agents/handoffAgent_initializer.py
python app/agents/cartManagerAgent_initializer.py
# ... etc
```

The initializer pattern:
```python
# 1. Load prompt
instructions = open("prompts/ShopperAgentPrompt.txt").read()

# 2. Discover MCP tools
tools = get_tools_for_agent_oneshot("cora")

# 3. Register in Foundry
agent = project_client.agents.create_version(
    model=deployment_name,
    name="cora",
    instructions=instructions,
    tools=tools,
)
```

### Step 3: Build the Handoff Router

The `HandoffService` classifies user intent using a Foundry agent with **structured output**:

```python
class IntentClassification(BaseModel):
    domain: Literal["cora", "interior_designer", "inventory_agent",
                     "customer_loyalty", "cart_manager"]
    is_domain_change: bool
    confidence: float
    reasoning: str
```

**Key file**: [src/services/handoff_service.py](../../src/services/handoff_service.py)

### Step 4: Add MCP Tools

MCP (Model Context Protocol) lets agents call tools over a standard protocol.

**Server** ([src/app/servers/mcp_inventory_server.py](../../src/app/servers/mcp_inventory_server.py)):
```python
from fastmcp import FastMCP
mcp = FastMCP("Zava Inventory Server")

@mcp.tool()
def get_product_recommendations(question: str) -> str:
    # Vector search in Cosmos DB
    ...
```

**Client** ([src/app/servers/mcp_inventory_client.py](../../src/app/servers/mcp_inventory_client.py)):
- Spawns the server as a subprocess over stdio
- Maintains persistent connection
- Exposes `call_tool()` method

### Step 5: Wire the Pipeline

The 5-step pipeline in [multi_agent_handler.py](../../src/handlers/multi_agent_handler.py):

```
classify_intent() → enrich_context() → execute_agent() → handle_image_creation() → process_response()
```

### Step 6: Add Observability

```python
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace

configure_azure_monitor(connection_string=os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"])
tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("Handoff Intent Classification"):
    agent_name = await classify_intent(...)
```

---

## Part D: A2A Protocol Agents

**Goal**: Build code-defined agents with `agent_framework` and expose them via the A2A protocol.

### Step 1: Define Agents

```python
from agent_framework import Agent, tool
from agent_framework.openai import OpenAIChatClient

client = OpenAIChatClient(model=deployment_name, async_client=async_openai)

product_agent = Agent(
    client=client,
    name="ProductAgent",
    instructions="You specialize in product information...",
    tools=get_products,  # @tool decorated function
)
```

### Step 2: Compose with `as_tool()`

```python
manager_agent = Agent(
    client=client,
    name="ProductManagerAgent",
    instructions="Delegate to the right sub-agent...",
    tools=[
        product_agent.as_tool(),
        marketing_agent.as_tool(),
        ranker_agent.as_tool(),
    ],
)
```

### Step 3: Add A2A Protocol Layer

```python
from a2a.server import A2AStarletteApplication, AgentCard, AgentSkill

agent_card = AgentCard(
    name="Zava Product Helper",
    skills=[AgentSkill(name="Product Management", ...)],
    capabilities=AgentCapabilities(streaming=True),
)

# Executor wraps your agent for A2A
class MyExecutor(AgentExecutor):
    async def execute(self, context, event_queue):
        result = await self.agent.invoke(context.get_user_input())
        event_queue.enqueue(TaskArtifactUpdateEvent(...))
```

### Step 4: Build the UI with SSE

```javascript
const response = await fetch('/api/chat/stream', {
    method: 'POST',
    body: JSON.stringify({ message, session_id }),
});
const reader = response.body.getReader();
// Read SSE events and update diagram + chat
```

---

## Part E: Collaborative Discussion

**Goal**: Build a multi-round agent-to-agent conversation with Manager-driven termination.

### Step 1: Define Opinionated Agents

Give each agent a **strong personality** so they naturally disagree:

```python
product_agent = Agent(
    name="ProductAgent",
    instructions="You care about ACCURACY. Push back if someone exaggerates...",
)
marketing_agent = Agent(
    name="MarketingAgent",
    instructions="You care about SALES. Challenge conservative approaches...",
)
```

### Step 2: Build the Orchestrator Loop

```python
async def discuss(self, scenario_prompt):
    transcript = []

    # Round 1: ProductAgent always first (gets data)
    message = await self._run_sub_agent("product", scenario_prompt, transcript)
    transcript.append({"agent_name": "ProductAgent", "message": message})

    # Rounds 2+: Manager decides who speaks next
    for round_num in range(2, MAX_ROUNDS + 1):
        decision = await self._ask_manager(scenario_prompt, transcript)

        if decision.decision == "conclude":
            yield {"type": "consensus", "summary": decision.summary}
            return

        message = await self._run_sub_agent(decision.next_agent, scenario_prompt, transcript)
        transcript.append(...)
```

### Step 3: Manager Termination with Structured Output

```python
class ManagerDecision(BaseModel):
    decision: Literal["continue", "conclude"]
    next_agent: str | None      # "product", "marketing", or "ranker"
    reason: str                  # Why this decision
    summary: str | None          # Only if concluding

response = await manager_agent.run(
    messages=prompt,
    options=OpenAIChatOptions(response_format=ManagerDecision),
)
```

---

## Common Patterns

### Session Management

All apps maintain session state differently:

| App | Session mechanism |
|-----|------------------|
| chat_app | WebSocket connection lifetime (in-memory variables) |
| a2a | `AgentSession` from agent_framework + session_id |
| a2ascenario | Fresh `AgentSession` per discussion |

### Error Handling

```python
# Pattern used across all apps
try:
    result = await agent.run(messages=user_input)
except Exception as e:
    logger.exception("Agent call failed")
    yield {"type": "error", "message": str(e)}
```

### Streaming

| App | Protocol | Pattern |
|-----|----------|---------|
| chat_app | WebSocket | `await websocket.send_text(json)` |
| a2a | SSE | `StreamingResponse(generate(), media_type="text/event-stream")` |
| a2ascenario | SSE | Same pattern |

---

## Next Steps

- [Demo Script](05-demo-script.md) — how to present this to an audience
- [Observability & Security](06-observability-and-security.md) — monitoring and red teaming
