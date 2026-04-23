"""FastAPI app for the A2A Collaborative Discussion scenario.

Standalone application — runs on its own port (default 8002) and is fully
independent of the original a2a/ solution.
"""
import asyncio
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from discussion_agent import MAX_ROUNDS, MIN_ROUNDS, discussion_agent

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pre-built discussion scenarios
# ---------------------------------------------------------------------------

SCENARIOS = {
    # --- Collaborative scenarios ---
    "product_launch": {
        "title": "Product Launch Review",
        "icon": "🚀",
        "category": "Collaborative",
        "description": (
            "The team reviews the Standard Paint Roller listing and refines "
            "its description, positioning, and recommended placement for an "
            "upcoming e-commerce launch."
        ),
        "prompt": (
            "Our team is preparing to launch the Standard Paint Roller on our e-commerce site. "
            "Discuss and agree on: (1) the final product description copy, (2) the target customer "
            "segment, and (3) where it should rank against our other rollers in the catalog."
        ),
    },
    "product_compare": {
        "title": "Flagship Product Selection",
        "icon": "🏆",
        "category": "Collaborative",
        "description": (
            "The team compares all paint rollers in the catalog and decides "
            "which one should be promoted as the flagship product on the homepage."
        ),
        "prompt": (
            "We need to choose ONE paint roller from our catalog to feature as the flagship product "
            "on our homepage hero banner. Discuss the candidates, weigh price vs. quality vs. brand image, "
            "and reach consensus on which one to feature and why."
        ),
    },
    "marketing_strategy": {
        "title": "Eco-Paint Marketing Strategy",
        "icon": "🌱",
        "category": "Collaborative",
        "description": (
            "The team develops a go-to-market strategy for the new eco-friendly "
            "paint line, covering positioning, audience, and product bundling."
        ),
        "prompt": (
            "We're launching our eco-friendly paint line (starting with Pale Meadow Eco Paint). "
            "Develop a go-to-market strategy: what's the positioning, who's the target customer, "
            "what accessories should we bundle with it, and how should we rank it in catalog search?"
        ),
    },
    # --- Debate scenarios (designed for disagreement) ---
    "price_hike": {
        "title": "Price Hike Debate",
        "icon": "💰",
        "category": "Debate",
        "description": (
            "Should we nearly double the Standard Paint Roller price from $8.49 to $14.99 "
            "and rebrand it as premium? The team has strong opposing views."
        ),
        "prompt": (
            "CONTROVERSIAL PROPOSAL: Management wants to raise the Standard Paint Roller price "
            "from $8.49 to $14.99 and rebrand it as 'Professional Grade.' "
            "Marketing thinks this is a great revenue opportunity. Product thinks the specs "
            "don't justify it. Ranker worries it will cannibalize the Eco-Friendly Roller at $15.99. "
            "Debate this honestly — disagree with each other if you think the other agent is wrong. "
            "Find a resolution the team can live with."
        ),
    },
    "budget_cut": {
        "title": "Product Line Cut",
        "icon": "🔥",
        "category": "Debate",
        "description": (
            "Budget cuts mean we must drop 2 of our 5 products. Which ones go? "
            "Every agent will fight for different products."
        ),
        "prompt": (
            "URGENT: Due to budget constraints, we MUST discontinue exactly 2 of our 5 products. "
            "The products are: (1) Eco-Friendly Paint Roller $15.99, (2) Standard Paint Roller $8.49, "
            "(3) Premium Paint Brush Set $25.49, (4) All-Purpose Paint Tray $9.99, "
            "(5) Pale Meadow Eco Paint $29.99. "
            "Each of you will have a different opinion on which to cut — argue your case strongly. "
            "Marketing: you care about brand image and revenue. Product: you care about catalog "
            "completeness. Ranker: you care about customer value. Disagree openly and find a compromise."
        ),
    },
    "competitor_response": {
        "title": "Competitor Price War",
        "icon": "⚔️",
        "category": "Debate",
        "description": (
            "A competitor just launched a $5.99 paint roller. Should we cut prices, "
            "differentiate, or bundle? Each agent has a different strategy."
        ),
        "prompt": (
            "CRISIS: Our main competitor just launched a basic paint roller at $5.99 — undercutting "
            "our cheapest roller ($8.49 Standard) by 30%%. Customers are already asking about it. "
            "We have three possible responses: (A) Cut prices to match, (B) Differentiate on quality "
            "and keep prices, (C) Create a bundle deal. "
            "Each of you MUST advocate for a DIFFERENT strategy and argue why the others are wrong. "
            "ProductAgent: defend our specs. MarketingAgent: think about positioning. "
            "RankerAgent: think about what customers actually want. Challenge each other directly."
        ),
    },
}


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Zava Agent Collaboration Lab",
    description="Multi-agent collaborative discussion demo (A2A scenario lab).",
    version="1.0.0",
)

base_path = Path(__file__).parent
app.mount("/static", StaticFiles(directory=base_path / "static"), name="static")
templates = Jinja2Templates(directory=base_path / "templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"scenarios": SCENARIOS, "max_rounds": MAX_ROUNDS, "min_rounds": MIN_ROUNDS},
    )


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "zava-agent-collaboration-lab"}


@app.get("/api/scenarios")
async def list_scenarios():
    return {
        sid: {k: v for k, v in s.items() if k != "prompt"}
        for sid, s in SCENARIOS.items()
    }


class DiscussRequest(BaseModel):
    scenario: str


@app.post("/api/discuss/stream")
async def discuss_stream(req: DiscussRequest):
    """Stream a multi-agent collaborative discussion via SSE."""
    scenario = SCENARIOS.get(req.scenario)
    if not scenario:
        return {"error": f"Unknown scenario: {req.scenario}"}

    async def generate():
        def send(event: dict) -> str:
            return f"data: {json.dumps(event)}\n\n"

        # Pre-amble events for diagram + flow log
        yield send({
            "type": "trace",
            "agent": "user",
            "status": "active",
            "msg": f"📝 User selected scenario: {scenario['title']}",
        })
        await asyncio.sleep(0.05)
        yield send({
            "type": "trace",
            "agent": "client",
            "status": "active",
            "msg": "📡 A2A Client wrapping scenario as discussion task",
        })
        await asyncio.sleep(0.05)
        yield send({
            "type": "trace",
            "agent": "server",
            "status": "active",
            "msg": "🌐 A2A Server received discussion task → routing to Manager",
        })
        await asyncio.sleep(0.05)
        yield send({
            "type": "trace",
            "agent": "manager",
            "status": "active",
            "msg": "🧠 Manager facilitating collaborative discussion...",
        })

        try:
            async for event in discussion_agent.discuss(scenario["prompt"]):
                # Mirror agent_turn events into trace updates for the diagram
                if event["type"] == "agent_turn":
                    yield send({
                        "type": "trace",
                        "agent": event["agent"],
                        "status": "active",
                        "msg": f"💬 {event['agent_name']} (round {event['round']}): "
                               f"{event['message'][:80]}{'...' if len(event['message']) > 80 else ''}",
                    })
                    yield send(event)
                    yield send({
                        "type": "trace",
                        "agent": event["agent"],
                        "status": "done",
                        "msg": f"✅ {event['agent_name']} finished turn",
                    })
                elif event["type"] == "manager_decision":
                    msg = (
                        f"🧠 Manager: {event['decision'].upper()}"
                        + (f" → next: {event['next_agent']}" if event["next_agent"] else "")
                        + f" ({event['reason']})"
                    )
                    yield send({
                        "type": "trace",
                        "agent": "manager",
                        "status": "active",
                        "msg": msg,
                    })
                    yield send(event)
                else:
                    yield send(event)

                # Small pause for UI animation pacing
                await asyncio.sleep(0.05)

            # Final trace
            yield send({
                "type": "trace",
                "agent": "manager",
                "status": "done",
                "msg": "🧠 Discussion concluded",
            })
            yield send({
                "type": "trace",
                "agent": "server",
                "status": "done",
                "msg": "🌐 A2A Server → final summary delivered",
            })
            yield send({
                "type": "trace",
                "agent": "client",
                "status": "done",
                "msg": "📡 A2A Client received summary",
            })
            yield send({
                "type": "trace",
                "agent": "user",
                "status": "done",
                "msg": "✅ Discussion delivered to user",
            })

        except Exception as e:  # noqa: BLE001
            logger.exception("Discussion failed")
            yield send({"type": "error", "message": str(e)})

        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("SCENARIO_HOST", "0.0.0.0")
    port = int(os.getenv("SCENARIO_PORT", 8002))
    uvicorn.run(app, host=host, port=port)
