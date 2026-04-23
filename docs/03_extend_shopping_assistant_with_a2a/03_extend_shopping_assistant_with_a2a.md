---
title: 'Exercise 03: Extend the shopping assistant using the A2A Protocol'
layout: default
nav_order: 4
has_children: true
---

# Exercise 03: Extend the shopping assistant using the A2A Protocol

## Scenario

In the previous exercise, you implemented a multimodal AI shopping assistant for Zava using Microsoft Foundry. The assistant allows customers to upload images, ask questions regarding the set of products available from Zava, and make purchases, all from a multimodal chat interface. However, Zava would like to extend the capabilities of the shopping assistant by integrating it with additional AI services and tools. This will allow the assistant to provide more personalized recommendations, improve the accuracy of product searches, and enhance the overall customer experience.

In this exercise, we will use the Agent2Agent (A2A) Protocol to enable communication between multiple AI agents. This will allow us to create a more sophisticated shopping assistant that can leverage the strengths of different AI models and services.

## Objectives

After you complete this exercise, you will be able to:

* Understand the A2A Protocol and its benefits
* Implement A2A communication between multiple AI agents

## Duration

* **Estimated Time:** 40 minutes

## Theory primer: Multi-Agent vs A2A (no workshop knowledge required)

> Read this first if you're new to the topic. The next section maps these ideas to the workshop, and the [advanced section](#advanced-orchestration-patterns-vs-the-a2a-protocol) goes deeper.

### What is an "agent"?

An **agent** is a program that uses a language model (LLM) to decide what to do. It usually has:

* a **system prompt** that tells it what role to play ("you are a paint expert"),
* optional **tools** (functions, APIs, databases) it can call,
* and a loop where it reads input → asks the LLM → maybe calls a tool → asks the LLM again → eventually returns an answer.

A **single-agent** system has one of these. **Multi-agent** means there is more than one.

### What is "multi-agent"?

**Multi-agent is a design choice, not a product.** It just means: instead of one big agent that does everything, you build several smaller agents that each specialise in something (paint, plumbing, billing…), and you arrange for them to work together.

The interesting part of multi-agent design is **how the agents are arranged to cooperate**. The common arrangements are:

| Arrangement | What it does |
|---|---|
| **Handoff (Router)** | A small classifier looks at the user's request and **picks one** specialist to handle it. The chosen specialist replies. |
| **Sequential (pipeline)** | Agent A → Agent B → Agent C. Fixed order. Each one's output feeds the next. (e.g. Researcher → Writer → Editor) |
| **Concurrent (parallel)** | Run several agents at the same time, then merge their answers. (e.g. send the same draft to 3 reviewers, average their scores) |
| **Manager / Magentic (orchestrator)** | A "manager" agent uses the other agents as **tools**. It decides at runtime which to call, in what order, possibly several times. |
| **Group chat** | All agents share one transcript and take turns. A moderator agent decides when to stop. |

These are all **multi-agent**. They differ in **who decides what runs next** (a classifier? a manager LLM? a fixed pipeline?) and **how many agents run per request** (one? many in sequence? many in parallel?).

> **Important:** "Multi-agent" by itself does **not** tell you whether the agents live in the same Python process, in different containers, in the cloud, or anywhere else. That's a separate decision.

### What is A2A?

**A2A (Agent2Agent Protocol)** is a **wire protocol** — a standard way for one agent to send a message to another agent **over the network**. Think of it like HTTP for agents, or like SMTP for email.

A2A defines three things:

1. **AgentCard** — a small JSON document published by every A2A agent. It describes the agent's name, what it can do, and the URL to call it. (Think: an OpenAPI spec for an agent.)
2. **Message format** — the exact JSON shape of a "task" sent to an agent and the events streamed back as a reply.
3. **Task lifecycle** — `submitted → working → completed` (or `failed`/`cancelled`), with optional cancellation and resumption.

That's all A2A is. It does **not** tell you:

* how many agents your system has,
* who decides which agent runs next,
* whether agents run in sequence or parallel,
* what language or framework each agent is written in.

### The key insight: they answer different questions

| Question | Answered by |
|---|---|
| "How is the work organised among my agents?" | **Multi-agent arrangement** (handoff, pipeline, parallel, manager, group chat) |
| "How do my agents physically send messages to each other?" | **Transport** (in-process function call, gRPC, REST, **A2A**, …) |

These are **independent**. You can have:

* Multi-agent **without** A2A — all agents in one Python process, calling each other as functions. Very common.
* A2A **without** multi-agent thinking — a single agent exposed at an A2A endpoint so other systems can call it.
* Multi-agent **with** A2A — each specialist runs in its own container/language, and they talk over A2A.

### Mental shortcut

> **Multi-agent** = a *style* of building (more than one specialist agent, arranged to cooperate).
> **A2A** = a *protocol* (the standard wire format agents use to talk to each other when they're not in the same process).

If two friends compare notes, that's "collaboration" (a style). Whether they do it by speaking, by phone, or by email is the "transport". Multi-agent is the collaboration style. A2A is one of the possible transports.

### When does each matter?

* You start caring about **multi-agent design** as soon as you have more than one agent and need to decide how they interact.
* You start caring about **A2A** when your agents need to be **independently deployable** — different teams, different languages, different release cycles, or callable by other organisations. If everything stays in one Python process, you don't need A2A; plain function calls work fine.

### Three common newbie misconceptions

1. **"A2A is a multi-agent pattern."** ❌ No — A2A is a transport. Any multi-agent pattern can run with or without A2A.
2. **"Multi-agent always means agents call each other over a network."** ❌ No — many multi-agent systems are entirely in-process. A2A is only needed when they're not.
3. **"If I'm using A2A, I'm doing multi-agent."** ❌ Not necessarily — you can expose one agent at an A2A endpoint with no other agents involved.

### TL;DR

* **Multi-agent** → *several specialised agents, arranged in some pattern (handoff, pipeline, parallel, manager, group chat).*
* **A2A** → *a standard HTTP/JSON protocol for one agent to talk to another over the network.*
* They are **orthogonal**. You can mix them however you like.

---

## Background: Multi-Agent (Exercise 02) vs A2A (Exercise 03) — what's the difference?

> Now that you've read the theory above, here's how those concepts map to the two exercises in this workshop.

This is the most common point of confusion. Both exercises have several agents. Both use an LLM to decide which agent runs. So **what's actually different?**

### The simple answer (read this first)

**"Multi-agent" and "A2A" aren't the same kind of thing.** Comparing them is like comparing **"a meeting"** with **"email"**.

* **Multi-agent** just means *"there is more than one agent"*. It doesn't say where the agents live or how they talk.
* **A2A** is a **protocol** — a wire format (HTTP + JSON) that lets agents send messages to each other.

So in this workshop, the real difference between the two exercises is:

| | **Exercise 02 — "Multi-Agent"** | **Exercise 03 — "A2A"** |
|---|---|---|
| **Where do the agents live?** | In **Microsoft Foundry** (cloud-managed service) | In your **Python process** (just objects in memory) |
| **How does the app call an agent?** | Foundry SDK call (`project_client.agents.run(agent_id, …)`) | Python function call via `agent.as_tool()`, wrapped with the A2A protocol so they could be called over HTTP |
| **What coordinates them?** | A small classifier LLM (`HandoffService`) returns one label like `"product"` and Python forwards the message to that one Foundry agent | A "manager" LLM (`ProductManagerAgent`) uses tool-calling to invoke sub-agents — possibly several, in any order — and writes the final reply itself |
| **Is the A2A protocol involved?** | No — calls go through the Foundry SDK | Yes — agents are wrapped as A2A endpoints |

So when this workshop says *"multi-agent vs A2A"*, what it really means is:

> **Foundry-managed agents called by SDK** (Exercise 02) vs **local Python agents wrapped with the A2A protocol** (Exercise 03).

That's the real difference. Everything else is detail.

### Store analogy

* **Exercise 02** is like a store where each department (paint, plumbing, loyalty) lives in its **own building** (= Foundry). A **receptionist** at the entrance listens to your question, decides which building you need, and sends you there. You then talk to that one department.
* **Exercise 03** is like a store where all the experts work in the **same room** (= your Python process). A **personal shopper** listens to your question, walks around to whichever experts he needs (sometimes more than one), gathers their input, and gives you the combined answer himself.

### Why does the workshop pair these two changes together?

Honestly — for teaching reasons. The two exercises differ on **two things at once** (where agents live *and* how they're coordinated), so it feels like one big jump. In real projects you can mix and match: you could host Foundry agents and have a Manager call them; you could have local Python agents and route them with a classifier; you could expose Foundry agents over A2A. The exercises just show the two most common combinations.

### The TL;DR for newbies

* **Multi-Agent in Exercise 02** = **agents in the cloud (Foundry)** + a **classifier** that picks one. Best for **production** apps with clearly separated domains.
* **A2A in Exercise 03** = **agents in your code** + a **manager LLM** that can call several. Best for **prototypes** and scenarios where one answer needs **multiple specialists** working together.

If you want to go deeper — including how A2A is actually a network protocol that's independent of *how* you orchestrate agents (handoff, sequential, parallel, manager, group chat…) — see the [advanced section below](#advanced-orchestration-patterns-vs-the-a2a-protocol).

---

## Advanced: orchestration patterns vs the A2A protocol

> ⚠️ Skip this section if you're just trying to get through the exercise. Come back when you start designing your own multi-agent system.

The summary above conflates two independent ideas to keep things simple. In reality there are **two separate dimensions**:

1. **Orchestration pattern** — *how* the work is organised among agents (handoff, sequential, parallel, manager, group chat…).
2. **Transport** — *how* agents actually send messages to each other (in-process function calls vs A2A protocol over HTTP).

### Orchestration patterns (HOW agents are arranged)

The Microsoft Agent Framework recognises around six common patterns:

| # | Pattern | What it does | Example in this workshop |
|---|---|---|---|
| 1 | **Single agent** | One agent answers everything | Exercise 02 / Task 01 |
| 2 | **Handoff (Router)** | A classifier picks ONE specialist per message | Exercise 02 / Task 02 (`HandoffService`) |
| 3 | **Sequential (pipeline)** | Agent A → Agent B → Agent C, fixed order | *not in workshop* — e.g. Researcher → Writer → Editor |
| 4 | **Concurrent (parallel)** | Run several agents at the same time, then merge | *not in workshop* — e.g. fan out to 3 reviewers, aggregate scores |
| 5 | **Manager / Magentic (orchestrator)** | A "manager" LLM dynamically calls sub-agents as tools, possibly many times, in any order | Exercise 03 (`ProductManagerAgent`) |
| 6 | **Group chat (collaborative)** | Agents take turns in a shared transcript, a moderator decides when to stop | Agent Collaboration Lab (`/collab-lab/`) |

These are **orchestration patterns**. They answer *"how is the work organised?"*

### A2A is **not** a pattern — it's a protocol

A2A (Agent2Agent Protocol) answers a completely different question: *"how do agents physically talk to each other over the network?"*

It defines:

* **AgentCard** — a JSON document that describes an agent's name, capabilities, and endpoint (think: an OpenAPI spec for an agent).
* **HTTP message format** — how to send a task to an agent and stream the reply.
* **Task lifecycle** — `submitted → working → completed/failed`, with cancellation and resumption.

A2A says **nothing** about whether your orchestration is sequential, parallel, handoff, or manager-style. **You can build any of the six patterns above with or without A2A.**

### Two-axis view — pattern × transport

| | **In-process** (Python imports, `as_tool()`, Foundry SDK) | **A2A Protocol** (over HTTP) |
|---|---|---|
| **Handoff (Router)** | ✅ Exercise 02 | Possible — router could POST to remote agent endpoints |
| **Sequential** | Most pipelines | Possible — chain agents on different servers |
| **Concurrent** | `asyncio.gather([agent_a.run(), agent_b.run()])` | Possible — fan out HTTP requests to multiple agent services |
| **Manager / Magentic** | Sub-agents wrapped with `.as_tool()` | ✅ Exercise 03 — sub-agents called via the A2A protocol |
| **Group chat** | ✅ Agent Collaboration Lab | Possible — each speaker could be a remote agent |

So the answer to *"can multi-agent run agents in parallel?"* is **yes — that's the Concurrent pattern**, and it's independent of A2A.

### What does A2A actually give you over plain function calls?

* **Independent deployment** — each agent can live in its own container, written in its own language (Python, .NET, Java…), maintained by a different team.
* **Discovery** — a manager or router can fetch an `AgentCard` from a URL and learn what an agent does at runtime, instead of hard-coding it.
* **Cross-org reuse** — your Marketing agent could be called by your own app **and** by a partner's app, without sharing code.
* **A standard wire format** — different SDKs and frameworks can interoperate.

### How this workshop maps to those concepts

| Workshop component | Orchestration pattern | Transport |
|---|---|---|
| Exercise 02 — Multi-Agent Shopping Assistant | **Handoff (Router)** | In-process (Foundry SDK calls) |
| Exercise 03 — A2A Demo (`ProductManagerAgent`) | **Manager / Magentic** | A2A Protocol |
| Agent Collaboration Lab | **Group chat** | In-process |

The two main exercises differ on **both** axes at once (different pattern *and* different transport), which is exactly why "multi-agent vs A2A" feels like a tangled comparison when you first read it.

### When to use which (quick guide)

| If you need to… | Exercise 02 style | Exercise 03 style |
|---|---|---|
| Send each user message to exactly one specialist | ✅ | |
| Combine output from multiple specialists in one reply | | ✅ |
| Get full Foundry features (tracing, evals, red teaming, versioning) | ✅ | |
| Prototype quickly with just Python + Azure OpenAI, no cloud agent registration | | ✅ |
| Expose each agent as an independently callable HTTP service | | ✅ |
| Keep latency and token cost low for simple Q&A | ✅ | |
| Let the orchestrator dynamically decide *how many* agents to involve per turn | | ✅ |

### TL;DR for newbies

* **Multi-Agent in Exercise 02** = **Router pattern**. A *Handoff Service* classifies intent and **routes** each message to one Foundry-managed agent. Best for **production** apps with clearly separated domains.
* **A2A in Exercise 03** = **Manager pattern**. A *ProductManagerAgent* **orchestrates** several local agents (defined in code) using `as_tool()` and the A2A Protocol. Best for **prototypes** and scenarios where one answer needs **multiple specialists** working together.

If you want a deeper side-by-side (including the two other patterns — single agent and collaborative discussion), see [Agent Patterns Comparison](../training/03-agent-patterns-comparison.md).
