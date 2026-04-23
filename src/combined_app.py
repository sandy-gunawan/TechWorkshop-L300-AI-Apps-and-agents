"""Combined entrypoint that mounts all 3 apps on one FastAPI instance.

Routes:
  /              → Multi-Agent Shopping Assistant (chat_app)
  /a2a-demo/     → A2A Protocol Demo
  /collab-lab/   → Agent Collaboration Lab

Usage:
  uvicorn combined_app:app --host 0.0.0.0 --port 8000
"""
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

load_dotenv()
logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).parent

# ── Ensure sub-app directories are importable ──
for sub in ("a2a", "a2ascenario"):
    p = str(BASE_DIR / sub)
    if p not in sys.path:
        sys.path.insert(0, p)

# ── Pre-load agent_framework before chat_app touches it ──
try:
    import agent_framework
    print(f"[COMBINED] agent_framework pre-loaded: Agent={hasattr(agent_framework, 'Agent')}", flush=True)
except Exception as e:
    print(f"[COMBINED] agent_framework pre-load failed: {e}", flush=True)

# ── Import the main shopping assistant app ──
from chat_app import app
print(f"[COMBINED] chat_app imported OK, routes before: {len(app.routes)}", flush=True)

# chat_app.py calls logging.basicConfig(level=WARNING) which suppresses the
# INFO-level "Function name: …" / "Function … succeeded" lines that the A2A
# trace pipeline uses to detect which sub-agent (Product/Marketing/Ranker) the
# Manager delegates to. Re-enable INFO for agent_framework so the live diagram
# can glow sub-agent nodes in real time.
logging.getLogger('agent_framework').setLevel(logging.INFO)
print("[COMBINED] agent_framework log level set to INFO for live trace", flush=True)

# ── Verify agent_framework still works after chat_app import ──
try:
    from agent_framework import Agent, AgentSession, tool
    print(f"[COMBINED] agent_framework re-check: Agent={Agent}, AgentSession={AgentSession}", flush=True)
except ImportError as e:
    print(f"[COMBINED] agent_framework BROKEN after chat_app import: {e}", flush=True)


# ===================================================================
# A2A Demo — mounted as routes + static files on the main app
# ===================================================================
try:
    print("[COMBINED] Importing A2A modules...", flush=True)
    # Import the A2A chat router (the SSE endpoint)
    # Use importlib to isolate from chat_app's agent_framework state
    import importlib
    _a2a_chat_mod = importlib.import_module("api.chat")
    _a2a_router = _a2a_chat_mod.router
    print("[COMBINED] api.chat imported OK", flush=True)

    _a2a_dir = BASE_DIR / "a2a"
    _a2a_templates = Jinja2Templates(directory=str(_a2a_dir / "templates"))

    # Static files for A2A UI
    app.mount("/a2a-demo/static", StaticFiles(directory=str(_a2a_dir / "static")), name="a2a-static")

    @app.get("/a2a-demo/", response_class=HTMLResponse)
    async def a2a_index(request: Request):
        return _a2a_templates.TemplateResponse(
            request=request, name="index.html",
            context={"base_path": "/a2a-demo"},
        )

    @app.get("/a2a-demo/health")
    async def a2a_health():
        return {"status": "healthy", "service": "a2a-demo"}

    # Router already declares prefix="/chat", so use /a2a-demo/api here
    # to get final paths like /a2a-demo/api/chat/stream
    app.include_router(_a2a_router, prefix="/a2a-demo/api", tags=["a2a"])

    print(f"[COMBINED] ✅ A2A routes added, total routes: {len(app.routes)}", flush=True)
except Exception as e:
    import traceback
    print(f"[COMBINED] ❌ A2A FAILED: {e}", flush=True)
    traceback.print_exc()


# ===================================================================
# Agent Collaboration Lab — mounted as routes on the main app
# ===================================================================
try:
    print("[COMBINED] Importing discussion_agent...", flush=True)
    from discussion_agent import MAX_ROUNDS, MIN_ROUNDS, discussion_agent as _disc_agent
    print("[COMBINED] discussion_agent imported OK", flush=True)

    _collab_dir = BASE_DIR / "a2ascenario"
    _collab_templates = Jinja2Templates(directory=str(_collab_dir / "templates"))

    # Import SCENARIOS from the scenario main module
    _scenario_main_path = _collab_dir / "main.py"
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("_scen_cfg", str(_scenario_main_path))
    _scen_mod = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_scen_mod)
    _SCENARIOS = _scen_mod.SCENARIOS

    # Static files for Collaboration Lab UI
    app.mount("/collab-lab/static", StaticFiles(directory=str(_collab_dir / "static")), name="collab-static")

    @app.get("/collab-lab/", response_class=HTMLResponse)
    async def collab_index(request: Request):
        return _collab_templates.TemplateResponse(
            request=request, name="index.html",
            context={"scenarios": _SCENARIOS, "max_rounds": MAX_ROUNDS, "min_rounds": MIN_ROUNDS,
                    "base_path": "/collab-lab"},
        )

    @app.get("/collab-lab/health")
    async def collab_health():
        return {"status": "healthy", "service": "collab-lab"}

    class _DiscussReq(BaseModel):
        scenario: str

    @app.post("/collab-lab/api/discuss/stream")
    async def collab_discuss_stream(req: _DiscussReq):
        scenario = _SCENARIOS.get(req.scenario)
        if not scenario:
            return {"error": f"Unknown scenario: {req.scenario}"}

        async def generate():
            def send(ev):
                return f"data: {json.dumps(ev)}\n\n"

            yield send({"type": "trace", "agent": "user", "status": "active", "msg": f"📝 Scenario: {scenario['title']}"})
            await asyncio.sleep(0.05)
            yield send({"type": "trace", "agent": "client", "status": "active", "msg": "📡 A2A Client wrapping scenario"})
            await asyncio.sleep(0.05)
            yield send({"type": "trace", "agent": "server", "status": "active", "msg": "🌐 Routing to Manager"})
            await asyncio.sleep(0.05)
            yield send({"type": "trace", "agent": "manager", "status": "active", "msg": "🧠 Manager facilitating discussion..."})

            try:
                async for event in _disc_agent.discuss(scenario["prompt"]):
                    if event["type"] == "agent_turn":
                        yield send({"type": "trace", "agent": event["agent"], "status": "active",
                                    "msg": f"💬 {event['agent_name']} (round {event['round']}): {event['message'][:80]}..."})
                        yield send(event)
                        yield send({"type": "trace", "agent": event["agent"], "status": "done",
                                    "msg": f"✅ {event['agent_name']} finished turn"})
                    elif event["type"] == "manager_decision":
                        msg = f"🧠 Manager: {event['decision'].upper()}"
                        if event.get("next_agent"):
                            msg += f" → next: {event['next_agent']}"
                        msg += f" ({event['reason']})"
                        yield send({"type": "trace", "agent": "manager", "status": "active", "msg": msg})
                        yield send(event)
                    else:
                        yield send(event)
                    await asyncio.sleep(0.05)

                for ag, st, msg in [("manager", "done", "🧠 Discussion concluded"),
                                     ("server", "done", "🌐 Summary delivered"),
                                     ("client", "done", "📡 Client received"),
                                     ("user", "done", "✅ Delivered to user")]:
                    yield send({"type": "trace", "agent": ag, "status": st, "msg": msg})
            except Exception as exc:
                logger.exception("Discussion failed")
                yield send({"type": "error", "message": str(exc)})
            yield "data: [DONE]\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")

    print(f"[COMBINED] ✅ Collab Lab routes added, total routes: {len(app.routes)}", flush=True)
except Exception as e:
    import traceback
    print(f"[COMBINED] ❌ Collab Lab FAILED: {e}", flush=True)
    traceback.print_exc()


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("combined_app:app", host="0.0.0.0", port=port)
