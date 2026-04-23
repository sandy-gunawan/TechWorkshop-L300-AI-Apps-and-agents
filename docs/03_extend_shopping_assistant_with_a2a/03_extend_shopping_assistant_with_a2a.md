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

## Background: Multi-Agent (Router) vs A2A (Manager) — what's the difference?

This is the most common point of confusion for people new to multi-agent systems. Exercise 02 and Exercise 03 both have "many agents working together," but they coordinate them in **two very different ways**.

### The two patterns at a glance

| | **Exercise 02 — Multi-Agent with Router** | **Exercise 03 — A2A with Manager** |
|---|---|---|
| **Coordinator name in the code** | `HandoffService` (the **Router**) | `ProductManagerAgent` (the **Manager**) |
| **What the coordinator does** | Reads the user message, **picks ONE** specialist agent, and forwards the message to it | Reads the user message, then **calls one or more** specialist agents as **tools** and combines their answers |
| **How the choice is made** | A small classifier LLM call returns an intent label (e.g. `product`, `cart`, `discount`) | The Manager's LLM decides at runtime which sub-agents to invoke via `as_tool()` |
| **Who talks to the user?** | The chosen specialist agent answers directly | The Manager answers, after gathering input from the specialists |
| **Where do agents live?** | Registered in **Microsoft Foundry** (cloud-managed) | Defined in **Python code** using the Microsoft Agent Framework |
| **Communication protocol** | Internal function calls inside your app | **A2A Protocol** over HTTP — agents are independently addressable |
| **Typical request flow** | User → Router → 1 agent → User | User → Manager → (Agent A + Agent B + Agent C) → Manager → User |

### Router vs Manager — the simple analogy

Think of a customer walking into a store:

* **Router (Exercise 02)** is like the **receptionist at the front desk**. She listens to your question, decides which department it belongs to (paint, plumbing, loyalty), and **sends you to that one department**. You then talk to that department directly. The receptionist is done.
* **Manager (Exercise 03)** is like a **personal shopping assistant**. He listens to your question, then walks around the store himself — asking the paint expert, the marketing person, and the product ranker — gathers their input, and comes back to you with a single combined answer. You only ever talk to the Manager.

So:

* **Router = picks one specialist, hands off, steps out.**
* **Manager = orchestrates several specialists, blends their answers, replies itself.**

### Why have both?

They solve different problems:

* **Router** is great when each user message clearly belongs to **one domain** (e.g. "What's my discount?" → only the loyalty agent matters). It's cheaper (one specialist call), easier to trace, and matches how Foundry's managed agents are typically used in production.
* **Manager** is great when answering a question **needs several skills at once** (e.g. "Recommend a paint roller and write me a catchy product description for it" → needs the Product agent **and** the Marketing agent). The Manager can call both and merge the result.

### "But both use an LLM to decide — what's actually different?"

This is the question that trips up almost every newcomer. Yes, both patterns use an LLM to make a decision. But **what the LLM is allowed to do with that decision is completely different**.

#### Router LLM — decides ONCE, then leaves

```text
User: "What paint do you have, and write me a catchy ad for it?"
        │
        ▼
┌───────────────────┐
│ Router LLM        │  Job: pick ONE label from a fixed list.
│ (HandoffService)  │  Returns: "product"   ← that's it. One word.
└───────┬───────────┘
        │
        ▼
   Cora (product agent)  ← only this agent runs
        │
        ▼
   Reply to user (probably ignores the "ad" part — Cora doesn't do marketing)
```

The Router LLM is a **classifier**. It reads the message and returns a single label like `"product"` or `"discount"`. It does **not** call any agents itself. Your Python code reads the label and calls **one** specialist. Done.

#### Manager LLM — decides REPEATEDLY, gathers, replies

```text
User: "What paint do you have, and write me a catchy ad for it?"
        │
        ▼
┌──────────────────────────────────────────────────┐
│ Manager LLM (ProductManagerAgent)                │
│  Job: hold a real conversation with itself,     │
│  using sub-agents as TOOLS.                      │
│                                                  │
│  Turn 1: call ProductAgent("paint")     ──► gets product list   │
│  Turn 2: call MarketingAgent(list)      ──► gets ad copy        │
│  Turn 3: write the final answer combining both  │
└───────┬──────────────────────────────────────────┘
        │
        ▼
   Reply to user (paint list + ad, both included)
```

The Manager LLM uses **tool calling** (the same mechanism that lets ChatGPT call `get_weather()`). Each sub-agent is wrapped with `.as_tool()` so the Manager sees them as functions it can invoke — possibly **many times, in any order**, before replying.

#### Side-by-side: what does the LLM actually return?

| | **Router LLM (Ex 02)** | **Manager LLM (Ex 03)** |
|---|---|---|
| What does the LLM return on its first call? | A label string: `"product"` | A tool call: `ProductAgent("paint")` |
| Then what? | Python code routes to that one agent. **The router LLM is done.** | The framework runs the tool, feeds the result back to the Manager LLM, which decides what to do next |
| How many sub-agents can run per user message? | **Exactly one** | **Zero, one, or many** |
| Who writes the final reply to the user? | The chosen specialist agent | The Manager itself (after collecting tool results) |
| LLM calls per user message | 2 (router + 1 specialist) | 2 to N (Manager + however many tool round-trips it needs) |

#### The "decide" they share is different in scope

* The **Router** decides **"which one of N buckets does this question belong to?"** — a classification. Single output. Single use.
* The **Manager** decides **"what should my next action be?"** — could be call agent A, then agent B, then write a reply, then call agent A again. It's a loop.

> A **router** is like a `switch` statement powered by an LLM.
> A **manager** is like a chatbot whose tools happen to be other chatbots.

#### A worked example — *"What paint do you have, and write me a catchy ad for it?"*

* **Router** would fail at this — it has to pick **either** Product **or** Marketing, not both.
* **Manager** handles it naturally: call Product → get the list → pass to Marketing → write the ad → combine into one reply.

That's the practical difference.

### "But multi-agent has many patterns — sequential, parallel, group chat… isn't A2A just one of them?"

Great question. This is where most newcomers get stuck, because the words "multi-agent" and "A2A" sound like they should be in the same category — but they're not.

#### Multi-agent **orchestration patterns** (HOW agents are arranged)

These describe the **shape of the workflow** — who talks to whom, in what order, and who decides. The Microsoft Agent Framework (and most orchestration libraries) commonly recognise around six:

| # | Pattern | What it does | Example in this workshop |
|---|---|---|---|
| 1 | **Single agent** | One agent answers everything | Exercise 02 / Task 01 |
| 2 | **Handoff (Router)** | A classifier picks ONE specialist per message | Exercise 02 / Task 02 (`HandoffService`) |
| 3 | **Sequential (pipeline)** | Agent A → Agent B → Agent C, fixed order | *not in workshop* — e.g. Researcher → Writer → Editor |
| 4 | **Concurrent (parallel)** | Run several agents at the same time, then merge | *not in workshop* — e.g. fan out to 3 reviewers, aggregate scores |
| 5 | **Manager / Magentic (orchestrator)** | A "manager" LLM dynamically calls sub-agents as tools, possibly many times, in any order | Exercise 03 (`ProductManagerAgent`) |
| 6 | **Group chat (collaborative)** | Agents take turns in a shared transcript, a moderator decides when to stop | Agent Collaboration Lab (`/collab-lab/`) |

All six are **orchestration patterns**. They answer the question *"how is the work organised?"*

#### A2A is **not** an orchestration pattern — it's a **protocol**

A2A (Agent2Agent Protocol) answers a completely different question: *"how do agents physically talk to each other over the network?"*

It defines:

* **AgentCard** — a JSON document that describes an agent's name, capabilities, and endpoint (think: an OpenAPI spec for an agent).
* **HTTP message format** — how to send a task to an agent and stream the reply.
* **Task lifecycle** — `submitted → working → completed/failed`, with cancellation and resumption.

A2A says **nothing** about whether your orchestration is sequential, parallel, handoff, or manager-style. You can build **any of the six patterns above with or without A2A**.

#### Two-axis view — pattern × transport

| | **In-process (just Python imports / `as_tool()`)** | **A2A Protocol (over HTTP)** |
|---|---|---|
| **Handoff (Router)** | Exercise 02 — agents live as Foundry IDs, router calls them in-process | Possible — router could POST to remote agent endpoints |
| **Sequential** | Most pipelines | Possible — chain agents on different servers |
| **Concurrent** | `asyncio.gather([agent_a.run(), agent_b.run()])` | Possible — fan out HTTP requests to multiple agent services |
| **Manager / Magentic** | Sub-agents wrapped with `.as_tool()` (the local part of Exercise 03) | Sub-agents called over the wire — true distributed orchestration |
| **Group chat** | Collab Lab — all agents in one Python process | Possible — each speaker could be a remote agent |

So the honest answer to *"can multi-agent do parallel too?"* is **yes — orchestration patterns are independent of A2A**.

#### Then what does A2A really give you?

* **Independent deployment** — each agent can live in its own container, written in its own language (Python, .NET, Java, etc.), maintained by a different team.
* **Discovery** — a manager or router can fetch an `AgentCard` from a URL and learn what an agent does at runtime, instead of hard-coding it.
* **Cross-org reuse** — your Marketing agent could be called by your own app **and** by a partner's app, without sharing code.
* **A standard wire format** — different SDKs and frameworks can interoperate.

In short:

> **Orchestration patterns** = how the work is organised (handoff, parallel, manager, group chat…).
> **A2A** = how agents send messages to each other over the network.
>
> They are **orthogonal**. You pick a pattern *and* you pick a transport.

#### How this workshop maps to those concepts

| Workshop component | Orchestration pattern | Transport |
|---|---|---|
| Exercise 02 — Multi-Agent Shopping Assistant | **Handoff (Router)** | In-process (Foundry SDK calls) |
| Exercise 03 — A2A Demo (`ProductManagerAgent`) | **Manager / Magentic** | A2A Protocol over HTTP |
| Agent Collaboration Lab | **Group chat** | In-process |

So when this workshop says *"multi-agent vs A2A"*, what it really means is:
*"Handoff pattern in Foundry"* vs *"Manager pattern speaking the A2A protocol"*.
The two examples differ on **both** axes at once, which is exactly why it feels like a tangle when you first read it.

### When to use which

| If you need to… | Use the **Router** pattern (Exercise 02) | Use the **Manager / A2A** pattern (Exercise 03) |
|---|---|---|
| Send each user message to exactly one specialist | ✅ | |
| Combine output from multiple specialists in one reply | | ✅ |
| Get full Foundry features (tracing, evals, red teaming, versioning) | ✅ | |
| Prototype quickly with just Python + Azure OpenAI, no cloud agent registration | | ✅ |
| Expose each agent as an independently callable HTTP service (so other apps / agents can talk to them) | | ✅ |
| Keep latency and token cost low for simple Q&A | ✅ | |
| Let the orchestrator dynamically decide *how many* agents to involve per turn | | ✅ |

### TL;DR for newbies

* **Multi-Agent in Exercise 02** = **Router pattern**. A *Handoff Service* classifies intent and **routes** each message to one Foundry-managed agent. Best for **production** apps with clearly separated domains.
* **A2A in Exercise 03** = **Manager pattern**. A *ProductManagerAgent* **orchestrates** several local agents (defined in code) using `as_tool()` and the A2A Protocol. Best for **prototypes** and scenarios where one answer needs **multiple specialists** working together.

If you want a deeper side-by-side (including the two other patterns — single agent and collaborative discussion), see [Agent Patterns Comparison](../training/03-agent-patterns-comparison.md).
