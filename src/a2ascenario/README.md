# Zava Agent Collaboration Lab (`a2ascenario`)

A **separate, isolated** demo app that adds a multi-agent collaborative
discussion experience on top of the same `agent_framework` primitives used
by the original `src/a2a/` solution.

> **The original `src/a2a/` solution is NOT modified.** This app lives in
> its own directory and runs on its own port.

## What it does

Three sub-agents — **ProductAgent**, **MarketingAgent**, **RankerAgent** —
take turns contributing to a discussion about a chosen scenario. After every
turn, the **ManagerAgent** decides whether to:

- **continue** → pick which agent should speak next, or
- **conclude** → write a final consensus summary.

The Manager has a **hard safety cap of 5 rounds**. Each agent sees the full
running transcript so they can build on, refine, or push back against
teammates' suggestions.

## Three pre-built scenarios

| Scenario | What the team discusses |
|----------|------------------------|
| 🚀 **Product Launch Review** | Final description, target audience, and catalog ranking for the Standard Paint Roller |
| 🏆 **Flagship Product Selection** | Which paint roller to feature on the homepage hero banner |
| 🌱 **Eco-Paint Marketing Strategy** | Positioning, audience, bundling, and search ranking for the new eco-paint line |

## How to run

From the `src/` directory:

```powershell
# Make sure you have the same env vars set as for the a2a/ app
# (gpt_endpoint, gpt_deployment) — the .env in src/ is auto-loaded.

cd a2ascenario
python main.py
```

By default the app listens on **port 8002**:

- Open <http://127.0.0.1:8002>
- The original `a2a/` app continues to work on **port 8001** unchanged.

You can override the port with the `SCENARIO_PORT` environment variable.

## Architecture

```
User clicks scenario card
   │
   ▼
POST /api/discuss/stream  (SSE)
   │
   ▼
CollaborativeDiscussionAgent.discuss(prompt)
   │
   ├── ManagerAgent picks first speaker
   │
   ├── Round 1: SelectedAgent.run(prompt + transcript)
   │   └── ManagerAgent.run → continue/conclude decision
   │
   ├── Round 2..N: NextAgent.run(prompt + transcript)
   │   └── ManagerAgent.run → continue/conclude decision
   │
   └── Final consensus summary
```

Key files:

- [`discussion_agent.py`](discussion_agent.py) — orchestration engine
- [`main.py`](main.py) — FastAPI app + SSE endpoint
- [`templates/index.html`](templates/index.html) — scenario picker + discussion view
- [`static/js/app.js`](static/js/app.js) — SSE client, message rendering, diagram animation
- [`static/css/style.css`](static/css/style.css) — styling

## Why is this isolated?

You asked specifically that this not touch the working `a2a/` solution.
The only shared resource is the `agent_framework` Python package itself
(installed in the project's virtual environment). All Python code, HTML,
CSS, and JS for this lab live entirely under `src/a2ascenario/`.
