# Demo Script

A presenter's guide for demonstrating the three apps. Each demo is self-contained — run them in order or pick one.

---

## Before the Demo

### Start all three apps

```powershell
# Terminal 1 — Multi-Agent Shopping (port 8000)
cd src
python -m uvicorn chat_app:app --port 8000

# Terminal 2 — A2A Protocol Demo (port 8001)
cd src/a2a
python main.py

# Terminal 3 — Agent Collaboration Lab (port 8002)
cd src/a2ascenario
python main.py
```

### Have these tabs open

- http://127.0.0.1:8000 — Shopping Assistant
- http://127.0.0.1:8001 — A2A Protocol Demo
- http://127.0.0.1:8002 — Agent Collaboration Lab
- Azure Portal → AI Foundry → Tracing (for Demo 1)

---

## Demo 1: Multi-Agent Shopping Assistant (5 min)

### What to show

**The idea**: A single chat interface backed by 6 specialized agents. A handoff router decides which agent handles each message. Agents use MCP tools to access real data.

### Script

**1. Product search** — show Cora and AI Search
> Type: *"What paint colors do you have for a living room?"*
>
> **Point out**: The handoff service routes this to Cora. Cora calls the MCP `get_product_recommendations` tool, which does a vector search in Cosmos DB. Products are returned with prices and images.

**2. Intent switch** — show handoff routing
> Type: *"Check if the Pale Meadow paint is in stock"*
>
> **Point out**: The handoff service detects a domain change (cora → inventory_agent). The inventory agent calls the `check_product_inventory` MCP tool. Notice the agent status indicators change in the UI.

**3. Cart management** — show agent specialization
> Type: *"Add 2 cans of Pale Meadow to my cart"*
>
> **Point out**: Routed to cart_manager. The cart state persists across the session. After the first cart operation, the customer loyalty agent (which started in the background) delivers a personalized discount.

**4. Foundry Tracing** (if Azure portal is available)
> Switch to Azure Portal → AI Foundry → Tracing
>
> **Point out**: Every agent call is traced — you can see the prompt, response, token usage, and latency for each step. This is automatic when using Foundry agents.

### Key talking points

- "The handoff agent is itself an LLM — it classifies intent using structured output"
- "MCP is a standard protocol — the tools could be written by a different team and even in a different language"
- "The customer loyalty calculation runs in the background, no blocking"
- "All agents share the same Azure OpenAI model — specialization comes from different prompts and tools"

---

## Demo 2: A2A Protocol Demo (3 min)

### What to show

**The idea**: A different approach — agents defined in Python code (not Foundry). The ProductManagerAgent delegates to sub-agents via `as_tool()`. The A2A protocol adds HTTP-based agent discovery.

### Script

**1. Product description improvement**
> Click the example: *"Make a better product description for the Standard Paint Roller."*
>
> **Point out the diagram**: Watch User → A2A Client → A2A Server → Manager light up in sequence. Then Manager delegates to ProductAgent (fetches catalog data) and potentially MarketingAgent (improves description).

**2. The Live Flow panel**
> **Point out**: Every step is logged in real time. You can see which sub-agent was called, when it completed, and the total execution time.

**3. The AgentCard**
> Open http://127.0.0.1:8001/agent-card in a new tab
>
> **Point out**: This is the A2A protocol's agent discovery mechanism. Other agents can find this agent's capabilities via HTTP.

### Key talking points

- "This uses `as_tool()` — the orchestrator agent decides at runtime which sub-agents to call"
- "No Foundry needed — agents are just Python objects calling Azure OpenAI"
- "The trade-off: you lose Foundry's tracing, versioning, and red teaming"
- "The A2A protocol is Google's open standard for inter-agent communication over HTTP"

---

## Demo 3: Agent Collaboration Lab (5 min)

### What to show

**The idea**: Agents can have real multi-turn conversations. Each agent sees what others said and can agree, disagree, or build on it. A Manager agent decides when the discussion is done.

### Script

**1. Collaborative scenario**
> Click **"🚀 Product Launch Review"** under the Collaborative section
>
> **Point out**: 
> - The user prompt appears at the top (blue bubble)
> - ProductAgent goes first (gets catalog data)
> - MarketingAgent builds on Product's data
> - RankerAgent provides ranking perspective
> - Manager decides to continue or conclude
> - Final consensus appears as a green "Response to User" card

**2. Debate scenario** (the highlight)
> Click **"← Choose another scenario"**, then click **"💰 Price Hike Debate"** under the Debate section
>
> **Point out the disagreements**:
> - ProductAgent says specs don't justify the price hike
> - MarketingAgent pushes back — "customers buy stories, not specs"
> - RankerAgent sides with ProductAgent — "this would cannibalize our eco line"
> - Manager keeps the debate going (doesn't conclude early)
> - Eventually agents find a compromise
>
> **This is the key moment**: "Notice how the Manager said CONTINUE because agents still disagreed. It only concluded after the disagreement was resolved."

**3. How-it-works bar**
> **Point out** the numbered steps at the top:
> ① User sends question → ② Agents discuss (min 4 turns) → ③ Manager decides → ④ Final answer to user

### Key talking points

- "Each agent sees the FULL transcript — that's why they can reference each other by name"
- "The Manager uses structured output to decide continue vs conclude — it's an LLM too"
- "Agent personalities matter — ProductAgent is data-driven, MarketingAgent is bold, RankerAgent champions the customer"
- "This pattern is great for demonstrating agent autonomy and collaboration"
- "Debate scenarios have agents with opposing viewpoints baked into their system prompts"

---

## FAQ / Anticipated Questions

### "Why three separate apps instead of one?"

Each demonstrates a different pattern with different trade-offs. In practice you'd pick ONE approach. Having all three lets you compare side by side.

### "Can I combine Foundry agents with the Agent Framework?"

Not directly — they're different SDKs. But you could have a Foundry agent call an A2A endpoint as a tool, creating a hybrid approach.

### "Why do agents always end up agreeing?"

In collaborative scenarios, agents are instructed to "build on teammates' suggestions." The debate scenarios have stronger personalities with opposing viewpoints, so they push back more.

### "Is the A2A protocol a Microsoft thing?"

No — A2A was proposed by Google as an open standard. Microsoft Agent Framework supports it. It's an HTTP-based protocol for agent discovery and task delegation.

### "How much does this cost to run?"

The main cost is Azure OpenAI tokens. A typical shopping session uses ~2K-5K tokens ($0.01-0.03). A collaboration discussion uses ~5K-15K tokens ($0.03-0.10) due to growing transcript. Infrastructure costs depend on the Container Apps configuration.

### "Can I add my own agents?"

Yes:
- **Foundry**: Create a new initializer script, write a prompt, register in Foundry
- **Agent Framework**: Define a new `Agent()` in Python and add it to the orchestrator
- **Collaboration Lab**: Add a new sub-agent to `discussion_agent.py`

---

## Next Steps

- [Observability & Security](06-observability-and-security.md) — monitoring and red teaming details
- [Project Structure Reference](07-project-structure-reference.md) — file-by-file guide
