# Project Structure Reference

A file-by-file guide to every file in the project. Use this as a lookup when you need to find where something is implemented.

---

## Directory Tree

```
TechWorkshop-L300-AI-Apps-and-Agents/
├── azure.yaml                          # Azure Developer CLI (azd) config
├── README.md                           # Project README
├── docs/                               # Workshop exercise docs (01-07)
├── media/Solution/                     # 120+ screenshots for exercises
│
└── src/                                # All application code
    ├── chat_app.py                     # ★ Main app: multi-agent shopping assistant (port 8000)
    ├── chat.html                       # Chat UI for chat_app
    ├── Dockerfile                      # Container image (Python 3.12-slim + uv)
    ├── pyproject.toml                  # Dependencies (agent-framework, azure-ai-agents, etc.)
    ├── env_sample.txt                  # Template for .env file
    ├── test_parsing.py                 # Unit tests for response parsing
    │
    ├── a2a/                            # ★ A2A Protocol Demo (port 8001)
    │   ├── main.py                     #   FastAPI app, mounts A2A server
    │   ├── agent/
    │   │   ├── product_management_agent.py  # 4 agents: Manager + Product/Marketing/Ranker
    │   │   ├── agent_executor.py       #   A2A AgentExecutor wrapper
    │   │   └── a2a_server.py           #   A2A protocol server + AgentCard
    │   ├── api/
    │   │   └── chat.py                 #   SSE streaming endpoint with live trace events
    │   ├── static/                     #   CSS, JS for chat UI + diagram
    │   └── templates/
    │       └── index.html              #   Chat interface with A2A diagram
    │
    ├── a2ascenario/                    # ★ Agent Collaboration Lab (port 8002)
    │   ├── main.py                     #   FastAPI app with 6 scenarios
    │   ├── discussion_agent.py         #   Multi-round discussion orchestrator
    │   ├── README.md                   #   Run instructions
    │   ├── static/                     #   CSS, JS for discussion UI
    │   └── templates/
    │       └── index.html              #   Scenario picker + discussion view
    │
    ├── app/                            # Shared agent definitions and tools
    │   ├── agents/
    │   │   ├── agent_initializer.py    #   Base class for Foundry agent registration
    │   │   ├── agent_processor.py      #   Runs Foundry agents via OpenAI Responses API
    │   │   ├── shopperAgent_initializer.py    # Registers Cora in Foundry
    │   │   ├── handoffAgent_initializer.py   # Registers handoff-service
    │   │   ├── cartManagerAgent_initializer.py
    │   │   ├── customerLoyaltyAgent_initializer.py
    │   │   ├── interiorDesignAgent_initializer.py
    │   │   ├── inventoryAgent_initializer.py
    │   │   ├── mcp_tools.py            #   MCP tool wrapper functions
    │   │   └── tool_definitions.py     #   MCP tool discovery + per-agent assignments
    │   ├── servers/
    │   │   ├── mcp_inventory_server.py #   FastMCP server (4 tools, stdio transport)
    │   │   └── mcp_inventory_client.py #   MCP client (subprocess + persistent connection)
    │   └── tools/
    │       ├── singleAgentExample.py   #   Simplest agent (raw OpenAI call)
    │       ├── aiSearchTools.py        #   Cosmos DB vector search for products
    │       ├── inventoryCheck.py       #   Simulated inventory data
    │       ├── discountLogic.py        #   Customer loyalty discount calculator
    │       ├── imageCreationTool.py    #   DALL-E image generation → Blob Storage
    │       ├── imageUnderstandingTool.py # Phi-4 image analysis
    │       └── understandImage.py      #   Image description helper
    │
    ├── handlers/
    │   ├── multi_agent_handler.py      #   5-step pipeline: classify → enrich → execute → image → process
    │   └── single_agent_handler.py     #   Simple single-agent handler (disabled)
    │
    ├── services/
    │   ├── handoff_service.py          #   LLM-based intent classification + domain routing
    │   ├── agent_service.py            #   AgentProcessor cache (by agent_type + agent_id)
    │   └── fallback_service.py         #   Fallback responses for errors
    │
    ├── prompts/                        #   System prompts for Foundry agents
    │   ├── ShopperAgentPrompt.txt      #   Cora — general shopping assistant
    │   ├── HandoffAgentPrompt.txt      #   Intent classifier (structured JSON output)
    │   ├── CartManagerPrompt.txt       #   Cart operations
    │   ├── CustomerLoyaltyAgentPrompt.txt  # Discount assignment
    │   ├── DiscountLogicPrompt.txt     #   Discount calculation logic
    │   ├── InteriorDesignAgentPrompt.txt   # Interior design + image creation
    │   ├── InventoryAgentPrompt.txt    #   Stock level checks
    │   └── aiSearchToolPrompt.txt      #   Product extraction from search results
    │
    ├── data/
    │   ├── product_catalog.json        #   54 products (paints, rollers, brushes, trays)
    │   ├── custom_attack_prompts.json  #   Red teaming adversarial prompts
    │   └── handoff_service_evaluation_grounded.jsonl  # Intent classification test cases
    │
    ├── utils/
    │   ├── env_utils.py                #   Environment variable loading + validation
    │   ├── history_utils.py            #   Chat history formatting + redaction
    │   ├── log_utils.py                #   Timing and cache logging helpers
    │   ├── message_utils.py            #   Rotating status messages + fast JSON
    │   ├── performance_utils.py        #   PerformanceMonitor (wall-clock timing)
    │   ├── response_utils.py           #   Response parsing + product extraction
    │   └── storage_utils.py            #   Azure Blob Storage helpers
    │
    ├── pipelines/
    │   └── ingest_to_cosmos.py         #   Load product_catalog.json → Cosmos DB with embeddings
    │
    ├── infra/
    │   ├── DeployAzureResources.bicep  #   Main Bicep template (all Azure resources)
    │   ├── updateRgTags.bicep          #   Resource group tag updates
    │   ├── check_quota.py              #   Check Azure OpenAI quota availability
    │   └── agents/                     #   Agent JSON definitions for Foundry
    │       ├── cora.json
    │       ├── handoff-service.json
    │       ├── cart-manager.json
    │       ├── customer-loyalty.json
    │       ├── interior-designer.json
    │       └── inventory-agent.json
    │
    └── workflows/
        ├── 0501_deployment.yml         #   GitHub Actions: build Docker → deploy to Container Apps
        └── 0502_sample_agent_deployment.yml  # GitHub Actions: deploy agent to Foundry via REST
```

---

## Environment Variables Reference

| Variable | Required by | Default | Description |
|----------|------------|---------|-------------|
| `FOUNDRY_ENDPOINT` | chat_app | — | Azure AI Foundry project endpoint |
| `gpt_endpoint` | all 3 apps | — | Azure OpenAI endpoint URL |
| `gpt_deployment` | all 3 apps | `gpt-5.4-mini` | Azure OpenAI model deployment name |
| `gpt_api_version` | all 3 apps | `2025-01-01-preview` | API version |
| `embedding_endpoint` | chat_app | — | Embedding model endpoint |
| `embedding_deployment` | chat_app | `text-embedding-3-large` | Embedding model name |
| `phi_4_endpoint` | chat_app | — | Phi-4 model endpoint (image understanding) |
| `phi_4_deployment` | chat_app | `Phi-4` | Phi-4 deployment name |
| `COSMOS_ENDPOINT` | chat_app | — | Cosmos DB endpoint URI |
| `DATABASE_NAME` | chat_app | `zava` | Cosmos DB database name |
| `CONTAINER_NAME` | chat_app | `product_catalog` | Cosmos DB container name |
| `storage_account_name` | chat_app | — | Azure Storage account name |
| `storage_container_name` | chat_app | `zava` | Blob container for images |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | chat_app | — | App Insights telemetry |
| `cora` | chat_app | `cora` | Foundry agent name for Cora |
| `handoff_service` | chat_app | `handoff-service` | Foundry agent name for handoff |
| `cart_manager` | chat_app | `cart-manager` | Foundry agent name for cart |
| `customer_loyalty` | chat_app | `customer-loyalty` | Foundry agent for loyalty |
| `interior_designer` | chat_app | `interior-designer` | Foundry agent for design |
| `inventory_agent` | chat_app | `inventory-agent` | Foundry agent for inventory |

---

## API Endpoints Reference

### chat_app.py (port 8000)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Serves `chat.html` UI |
| GET | `/health` | Health check |
| WebSocket | `/ws` | Main chat connection |

### a2a/main.py (port 8001)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Serves A2A chat UI |
| GET | `/health` | Health check |
| GET | `/agent-card` | A2A protocol agent discovery |
| POST | `/api/chat/stream` | SSE streaming chat |
| POST | `/a2a/tasks/send` | A2A protocol task submission |

### a2ascenario/main.py (port 8002)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Serves Collaboration Lab UI |
| GET | `/health` | Health check |
| GET | `/api/scenarios` | List available scenarios |
| POST | `/api/discuss/stream` | SSE streaming discussion |

---

## Port Assignments

| Port | App | Framework |
|------|-----|-----------|
| 8000 | Multi-Agent Shopping Assistant | Azure AI Foundry Agents |
| 8001 | A2A Protocol Demo | Microsoft Agent Framework + A2A |
| 8002 | Agent Collaboration Lab | Microsoft Agent Framework |

---

## Agent Inventory (All Apps)

### Foundry Agents (chat_app — port 8000)

| Agent | Foundry Name | Prompt | Tools | Purpose |
|-------|-------------|--------|-------|---------|
| Handoff Service | `handoff-service` | `HandoffAgentPrompt.txt` | — | Intent classification |
| Cora | `cora` | `ShopperAgentPrompt.txt` | `get_product_recommendations` | General shopping |
| Interior Designer | `interior-designer` | `InteriorDesignAgentPrompt.txt` | `get_product_recommendations` | Room design |
| Inventory Agent | `inventory-agent` | `InventoryAgentPrompt.txt` | `check_product_inventory` | Stock levels |
| Customer Loyalty | `customer-loyalty` | `CustomerLoyaltyAgentPrompt.txt` | `get_customer_discount` | Discounts |
| Cart Manager | `cart-manager` | `CartManagerPrompt.txt` | — | Cart operations |

### Agent Framework Agents (a2a — port 8001)

| Agent | Role | Tools | Composition |
|-------|------|-------|-------------|
| ProductManagerAgent | Orchestrator | Product/Marketing/Ranker `as_tool()` | Delegates to sub-agents |
| ProductAgent | Product data | `get_products` @tool | Called as tool |
| MarketingAgent | Marketing strategy | — | Called as tool |
| RankerAgent | Product ranking | — | Called as tool |

### Agent Framework Agents (a2ascenario — port 8002)

| Agent | Role | Personality | Tools |
|-------|------|-------------|-------|
| ProductAgent | Product data | Accuracy — pushes back on hype | `get_products` @tool |
| MarketingAgent | Marketing | Boldness — advocates premium | — |
| RankerAgent | Customer value | Customer-first — calls out overpricing | — |
| ManagerAgent | Facilitator | Neutral — decides continue/conclude | — |

---

## Next Steps

- [Solution Overview](01-solution-overview.md) — start from the beginning
- [Architecture Deep Dive](02-architecture-deep-dive.md) — diagrams and flows
- [Agent Patterns Comparison](03-agent-patterns-comparison.md) — decision guide
