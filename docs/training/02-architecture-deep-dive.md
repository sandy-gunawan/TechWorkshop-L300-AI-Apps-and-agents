# Architecture Deep Dive

This document covers the architecture of all three apps with diagrams and code-level flow walkthroughs.

---

## System Architecture

```mermaid
graph TB
    subgraph "User"
        Browser["Browser"]
    end

    subgraph "Applications"
        APP1["chat_app.py<br/>:8000 — WebSocket"]
        APP2["a2a/main.py<br/>:8001 — SSE"]
        APP3["a2ascenario/main.py<br/>:8002 — SSE"]
    end

    subgraph "Azure AI Foundry"
        PROJ["AI Foundry Project"]
        AGENTS["6 Registered Agents<br/>handoff-service, cora,<br/>cart-manager, customer-loyalty,<br/>interior-designer, inventory-agent"]
        TRACE["Foundry Tracing"]
    end

    subgraph "Azure OpenAI"
        GPT["GPT-5.4-mini"]
        EMB["text-embedding-3-large"]
        PHI["Phi-4"]
        DALLE["gpt-image-1"]
    end

    subgraph "Data Layer"
        COSMOS["Cosmos DB<br/>NoSQL + Vector Search"]
        SEARCH["AI Search"]
        BLOB["Blob Storage<br/>Product Images"]
    end

    subgraph "Observability"
        OTEL["OpenTelemetry"]
        APPINS["Application Insights"]
        LOGANA["Log Analytics"]
    end

    subgraph "Deployment"
        ACR["Container Registry"]
        ACA["Container Apps"]
    end

    Browser --> APP1
    Browser --> APP2
    Browser --> APP3

    APP1 --> PROJ --> AGENTS
    AGENTS --> GPT
    APP1 --> EMB
    APP1 --> PHI
    APP1 --> DALLE
    APP1 --> COSMOS
    APP1 --> SEARCH
    APP1 --> BLOB
    APP1 --> OTEL --> APPINS --> LOGANA

    APP2 --> GPT
    APP3 --> GPT

    APP1 --> ACA
    ACR --> ACA

    PROJ --> TRACE

    style AGENTS fill:#2563eb,color:#fff
    style GPT fill:#7c3aed,color:#fff
    style COSMOS fill:#10b981,color:#fff
```

---

## App 1: Multi-Agent Shopping Assistant

### Architecture

```mermaid
graph LR
    User["👤 User<br/>Browser"]
    WS["WebSocket<br/>chat_app.py"]
    HS["HandoffService<br/>Intent Router"]

    subgraph "Foundry Agents"
        CORA["Cora<br/>Shopping"]
        ID["Interior<br/>Designer"]
        INV["Inventory<br/>Agent"]
        CL["Customer<br/>Loyalty"]
        CM["Cart<br/>Manager"]
    end

    subgraph "MCP Tools (stdio)"
        MCPS["MCP Server<br/>FastMCP"]
        T1["AI Search<br/>Products"]
        T2["Inventory<br/>Check"]
        T3["Discount<br/>Calculator"]
        T4["Image<br/>Generator"]
    end

    User -->|"JSON"| WS
    WS -->|"classify"| HS
    HS -->|"route"| CORA
    HS -->|"route"| ID
    HS -->|"route"| INV
    HS -->|"route"| CL
    HS -->|"route"| CM

    CORA -->|"function_call"| MCPS
    ID -->|"function_call"| MCPS
    INV -->|"function_call"| MCPS
    CL -->|"function_call"| MCPS

    MCPS --> T1
    MCPS --> T2
    MCPS --> T3
    MCPS --> T4

    style HS fill:#f59e0b,color:#000
    style MCPS fill:#10b981,color:#fff
```

### Code Flow: User Message → Response

```
1. User sends WebSocket message
   └─ chat_app.py: websocket_endpoint()

2. Parse JSON: {message, image_url, conversation_history, cart}
   └─ orjson.loads(data)

3. Background: Customer loyalty (once per session)
   └─ asyncio.create_task(run_customer_loyalty_task())
   └─ Calls customer-loyalty Foundry agent
   └─ Stores discount % for later

4. Classify intent → select agent
   └─ handlers/multi_agent_handler.py: classify_intent()
   └─ services/handoff_service.py: HandoffService.classify()
   └─ LLM call to handoff-service agent
   └─ Returns: {domain: "cora", confidence: 0.95}
   └─ Maps domain → Foundry agent ID from env vars

5. Enrich context
   └─ handlers/multi_agent_handler.py: enrich_context()
   └─ If image_url → get cached image description (Phi-4)
   └─ If cora/interior_designer → vector search for products
   └─ Build enriched message string

6. Execute agent
   └─ handlers/multi_agent_handler.py: execute_agent()
   └─ services/agent_service.py: get_or_create_agent_processor()
   └─ app/agents/agent_processor.py: AgentProcessor.run_conversation_with_text_stream()
   └─ OpenAI Responses API with agent_reference
   └─ If agent requests function_call:
       └─ app/agents/mcp_tools.py: MCP_FUNCTIONS[tool_name]()
       └─ app/servers/mcp_inventory_client.py → stdio → mcp_inventory_server.py
       └─ Feed tool result back → get final response

7. Process response
   └─ handlers/multi_agent_handler.py: process_response()
   └─ Parse JSON, update cart, persist discount %
   └─ Send response over WebSocket
```

### Agent Inventory

| Agent | Foundry Name | Prompt File | MCP Tools | Role |
|-------|-------------|-------------|-----------|------|
| **Handoff Service** | `handoff-service` | `HandoffAgentPrompt.txt` | — | Intent classification → routes to correct agent |
| **Cora** | `cora` | `ShopperAgentPrompt.txt` | `get_product_recommendations` | General shopping assistant, product browsing |
| **Interior Designer** | `interior-designer` | `InteriorDesignAgentPrompt.txt` | `get_product_recommendations` | Room design, color schemes, image creation |
| **Inventory Agent** | `inventory-agent` | `InventoryAgentPrompt.txt` | `check_product_inventory` | Stock levels and availability |
| **Customer Loyalty** | `customer-loyalty` | `CustomerLoyaltyAgentPrompt.txt` | `get_customer_discount` | Personalized discount calculation |
| **Cart Manager** | `cart-manager` | `CartManagerPrompt.txt` | — | Add/remove items, checkout |

### MCP Tool Flow

```mermaid
sequenceDiagram
    participant Agent as Foundry Agent
    participant AP as AgentProcessor
    participant MC as MCP Client
    participant MS as MCP Server (stdio)
    participant Tool as Tool Implementation

    Agent->>AP: function_call: "get_product_recommendations"
    AP->>MC: call_tool("get_product_recommendations", {question})
    MC->>MS: JSON-RPC over stdio
    MS->>Tool: product_recommendations(question)
    Tool->>Tool: Embed query → Cosmos DB vector search
    Tool-->>MS: Product results
    MS-->>MC: JSON-RPC response
    MC-->>AP: Tool output
    AP->>Agent: Submit tool output
    Agent-->>AP: Final text response
```

---

## App 2: A2A Protocol Demo

### Architecture

```mermaid
graph TB
    User["👤 User"]
    UI["Chat UI<br/>index.html"]
    API["FastAPI<br/>/api/chat/stream (SSE)"]

    subgraph "A2A Protocol Layer"
        A2AC["A2A Client"]
        A2AS["A2A Server<br/>/a2a/tasks/send"]
        AE["AgentExecutor"]
        AC["AgentCard<br/>/agent-card"]
    end

    subgraph "Agent Framework Agents"
        PM["ProductManagerAgent<br/>Orchestrator"]
        PA["ProductAgent<br/>as_tool()"]
        MA["MarketingAgent<br/>as_tool()"]
        RA["RankerAgent<br/>as_tool()"]
    end

    GP["get_products<br/>@tool"]
    AOAI["Azure OpenAI"]

    User --> UI --> API
    API --> A2AC --> A2AS --> AE --> PM
    PM --> PA --> GP
    PM --> MA
    PM --> RA
    PA --> AOAI
    MA --> AOAI
    RA --> AOAI

    style PM fill:#7c3aed,color:#fff
    style PA fill:#10b981,color:#fff
    style MA fill:#f59e0b,color:#fff
    style RA fill:#3b82f6,color:#fff
```

### Code Flow

```
1. User sends message via chat UI
   └─ POST /api/chat/stream

2. SSE stream starts
   └─ a2a/api/chat.py: stream_message()
   └─ Emit trace events: user → client → server → manager

3. Agent execution
   └─ a2a/agent/product_management_agent.py: invoke()
   └─ ProductManagerAgent.run(message, session)
   └─ LLM decides which sub-agents to call via as_tool()

4. Sub-agent delegation (automatic via agent_framework)
   └─ ProductAgent.run() → calls get_products @tool
   └─ MarketingAgent.run() → returns marketing advice
   └─ RankerAgent.run() → returns ranking

5. Real-time log capture
   └─ LiveLogHandler captures agent_framework logs
   └─ Detects "Function name:" → emits trace SSE events
   └─ UI diagram lights up per agent

6. Final response
   └─ Structured ResponseFormat {status, message}
   └─ Emitted as SSE response event
```

### Key Concept: `as_tool()`

Sub-agents are exposed as **tools** on the orchestrator agent:

```python
# Each sub-agent becomes a callable tool
self.agent = Agent(
    name="ProductManagerAgent",
    tools=[
        product_agent.as_tool(),    # LLM can call ProductAgent
        marketing_agent.as_tool(),  # LLM can call MarketingAgent
        ranker_agent.as_tool(),     # LLM can call RankerAgent
    ],
)
```

The LLM decides **at runtime** which sub-agents to invoke — it can call one, multiple, or none.

---

## App 3: Agent Collaboration Lab

### Architecture

```mermaid
graph TB
    User["👤 User picks scenario"]
    API["POST /api/discuss/stream<br/>SSE"]

    subgraph "Discussion Orchestrator"
        DISC["discuss() async generator"]
        LOOP["Round Loop<br/>max 8 rounds, min 4"]
    end

    subgraph "Agents (individual agent.run() calls)"
        PA["📦 ProductAgent<br/>Accuracy & Data"]
        MA["📣 MarketingAgent<br/>Boldness & Sales"]
        RA["🏆 RankerAgent<br/>Customer Value"]
    end

    MGR["🧠 ManagerAgent<br/>Decides: continue or conclude"]

    User --> API --> DISC --> LOOP
    LOOP -->|"Round N"| PA
    LOOP -->|"Round N"| MA
    LOOP -->|"Round N"| RA
    LOOP -->|"After each turn"| MGR
    MGR -->|"continue + next_agent"| LOOP
    MGR -->|"conclude + summary"| API

    style MGR fill:#a855f7,color:#fff
    style PA fill:#10b981,color:#fff
    style MA fill:#f59e0b,color:#fff
    style RA fill:#3b82f6,color:#fff
```

### Discussion Flow

```mermaid
sequenceDiagram
    participant U as User
    participant O as Orchestrator
    participant P as ProductAgent
    participant Mk as MarketingAgent
    participant R as RankerAgent
    participant M as Manager

    U->>O: Select scenario (e.g., "Price Hike Debate")

    rect rgb(20, 40, 60)
        Note over O: Round 1 (always ProductAgent first)
        O->>P: Scenario + empty transcript
        P-->>O: "Standard Roller is $8.49, specs don't justify $14.99"
    end

    O->>M: Transcript (1 turn) — who's next?
    M-->>O: continue → MarketingAgent

    rect rgb(40, 30, 10)
        Note over O: Round 2
        O->>Mk: Scenario + transcript
        Mk-->>O: "I disagree — perception matters more than specs"
    end

    O->>M: Transcript (2 turns) — who's next?
    M-->>O: continue → RankerAgent

    rect rgb(10, 30, 50)
        Note over O: Round 3
        O->>R: Scenario + transcript
        R-->>O: "At $14.99 it undercuts our own Eco-Friendly roller"
    end

    O->>M: Transcript (3 turns) — who's next?
    M-->>O: continue → MarketingAgent (challenged)

    rect rgb(40, 30, 10)
        Note over O: Round 4
        O->>Mk: Scenario + transcript
        Mk-->>O: "Fair point. Counter-proposal: $11.99 as Best Value tier"
    end

    O->>M: Transcript (4 turns) — who's next?
    M-->>O: conclude ✅
    O-->>U: Summary: "Compromise at $11.99 with Best Value positioning"
```

### Key Concept: Full Transcript Sharing

Unlike `as_tool()` (App 2), each agent in the Collaboration Lab sees the **entire conversation history**:

```python
user_message = f"""
=== SCENARIO ===
{scenario_prompt}

=== DISCUSSION SO FAR ===
Turn 1 [ProductAgent]: Standard Roller is $8.49...
Turn 2 [MarketingAgent]: I disagree — perception matters...

=== YOUR TURN ===
You are RankerAgent. Reply in 1-2 SHORT sentences.
"""
response = await agent.run(messages=user_message, session=session)
```

This enables agents to **reference each other by name**, **agree or disagree**, and **build on prior turns**.

---

## Data Flow

```mermaid
graph LR
    JSON["product_catalog.json<br/>54 products"]
    INGEST["ingest_to_cosmos.py"]
    COSMOS["Cosmos DB<br/>NoSQL container"]
    EMB["text-embedding-3-large<br/>Generate embeddings"]
    SEARCH["Cosmos DB<br/>Vector Search"]
    MCP["MCP Tool<br/>get_product_recommendations"]
    AGENT["Agent uses<br/>search results"]

    JSON --> INGEST --> COSMOS
    COSMOS --> EMB --> COSMOS
    COSMOS --> SEARCH --> MCP --> AGENT

    style COSMOS fill:#10b981,color:#fff
    style MCP fill:#f59e0b,color:#000
```

1. `product_catalog.json` (54 products: paints, rollers, brushes, trays) is ingested into Cosmos DB
2. Each product gets a vector embedding via `text-embedding-3-large`
3. When an agent calls `get_product_recommendations`, the MCP tool runs a **vector search** on Cosmos DB
4. Results are returned to the agent as context for generating responses

---

## Infrastructure (Azure Resources from Bicep)

| Resource | Type | Purpose |
|----------|------|---------|
| **Cosmos DB** | NoSQL | Product catalog with vector search |
| **Storage Account** | Blob | Product images, AI-generated images |
| **AI Foundry** (AIServices) | Cognitive Services | Hosts AI models + Foundry project |
| **AI Project** | Foundry Project | Agent management, tracing, evaluations |
| **Log Analytics** | Workspace | Log aggregation (90-day retention) |
| **Application Insights** | Monitoring | Traces, metrics, logs from apps |
| **Container Registry** | ACR | Docker image storage |
| **Container Apps Environment** | ACA | Serverless container hosting |
| **Container App** | ACA | Runs the chat_app (1 CPU, 2GB RAM) |

All resources share a single resource group and use **Managed Identity** for authentication (no API keys).

---

## Next Steps

- [Agent Patterns Comparison](03-agent-patterns-comparison.md) — when to use which approach
- [Implementation Guide](04-implementation-guide.md) — build it step by step
