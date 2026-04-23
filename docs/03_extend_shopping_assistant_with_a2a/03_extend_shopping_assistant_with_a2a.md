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
