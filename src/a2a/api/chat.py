import uuid
import time
import io
import json
import logging
import asyncio
import queue
from typing import Dict

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent.product_management_agent import AgentFrameworkProductManagementAgent

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/chat", tags=["chat"])

# In-memory session store (in production, use Redis or database)
product_management_agent = AgentFrameworkProductManagementAgent()
active_sessions: Dict[str, str] = {}


class ChatMessage(BaseModel):
    """Chat message model"""
    message: str
    session_id: str = None


class ChatResponse(BaseModel):
    """Chat response model"""
    response: str
    session_id: str
    is_complete: bool
    requires_input: bool
    trace: list = []


class LiveLogHandler(logging.Handler):
    """Custom log handler that captures agent_framework logs into a queue."""
    def __init__(self, q):
        super().__init__()
        self.q = q
    def emit(self, record):
        self.q.put(self.format(record))


@router.post("/stream")
async def stream_message(chat_message: ChatMessage):
    """Stream real-time agent trace events via SSE, then the final response."""
    session_id = chat_message.session_id or str(uuid.uuid4())
    active_sessions[session_id] = session_id

    async def generate():
        def send_event(data):
            return f"data: {json.dumps(data)}\n\n"

        # Phase 1: Pre-execution trace (sent immediately)
        yield send_event({"type": "trace", "agent": "user", "status": "active",
            "msg": f'📝 User: "{chat_message.message[:80]}{"..." if len(chat_message.message) > 80 else ""}"'})
        yield send_event({"type": "trace", "agent": "client", "status": "active",
            "msg": "📡 A2A Client wrapping message as task → POST /tasks/send"})
        await asyncio.sleep(0.05)

        yield send_event({"type": "trace", "agent": "server", "status": "active",
            "msg": "🌐 A2A Server received task → created task ID → routing to AgentExecutor"})
        await asyncio.sleep(0.05)

        yield send_event({"type": "trace", "agent": "manager", "status": "active",
            "msg": "🧠 ProductManagerAgent analyzing intent and selecting sub-agents..."})
        await asyncio.sleep(0.05)

        # Phase 2: Set up log capture for real-time agent detection
        log_q = queue.Queue()
        handler = LiveLogHandler(log_q)
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter('%(message)s'))
        af_logger = logging.getLogger('agent_framework')
        af_logger.addHandler(handler)

        agent_names = {'ProductAgent': ('product', '📦'), 'MarketingAgent': ('marketing', '📣'), 'RankerAgent': ('ranker', '🏆')}
        seen_active = set()
        seen_done = set()
        collected_logs = []

        # Phase 3: Run agent in background task, poll logs
        result_holder = {}
        error_holder = {}

        async def run_agent():
            try:
                result_holder['response'] = await product_management_agent.invoke(chat_message.message, session_id)
            except Exception as e:
                error_holder['error'] = str(e)

        start = time.time()
        task = asyncio.create_task(run_agent())

        # Poll for log events while agent is running
        while not task.done():
            await asyncio.sleep(0.3)
            # Drain log queue
            while not log_q.empty():
                try:
                    line = log_q.get_nowait()
                    collected_logs.append(line)

                    # Detect agent calls in real-time
                    # agent_framework log lines look like:
                    #   "name: MarketingAgent"        (function invoke)
                    #   "MarketingAgent succeeded."   (function done)
                    stripped = line.strip()
                    func_name = None
                    if stripped.startswith('name:'):
                        func_name = stripped.split(':', 1)[1].strip()
                    elif 'Function name:' in stripped:
                        func_name = stripped.split('Function name:')[-1].strip()
                    if func_name:
                        if func_name in agent_names and func_name not in seen_active:
                            seen_active.add(func_name)
                            aid, icon = agent_names[func_name]
                            yield send_event({"type": "trace", "agent": aid, "status": "active",
                                "msg": f"{icon} Manager delegating to {func_name} via as_tool()..."})
                        elif func_name == 'get_products' and 'get_products' not in seen_active:
                            seen_active.add('get_products')
                            yield send_event({"type": "trace", "agent": "product", "status": "active",
                                "msg": "✍️ ProductAgent → calling get_products tool to fetch catalog..."})

                    # Detect completions: "<Name> succeeded." or "Function <Name> succeeded"
                    done_name = None
                    if stripped.endswith('succeeded.') or stripped.endswith('succeeded'):
                        token = stripped.rsplit(' succeeded', 1)[0].strip()
                        # Strip leading "Function " if present
                        if token.startswith('Function '):
                            token = token[len('Function '):].strip()
                        done_name = token
                    if done_name:
                        if done_name in agent_names and done_name not in seen_done:
                            seen_done.add(done_name)
                            aid, icon = agent_names[done_name]
                            yield send_event({"type": "trace", "agent": aid, "status": "done",
                                "msg": f"{icon} {done_name} completed → returned results to Manager"})
                        elif done_name == 'get_products' and 'get_products' not in seen_done:
                            seen_done.add('get_products')
                            yield send_event({"type": "trace", "agent": "product", "status": "done",
                                "msg": "📦 get_products returned catalog data"})
                except queue.Empty:
                    break

        # Drain any remaining logs
        while not log_q.empty():
            try:
                line = log_q.get_nowait()
                collected_logs.append(line)
                stripped = line.strip()
                func_name = None
                if stripped.startswith('name:'):
                    func_name = stripped.split(':', 1)[1].strip()
                elif 'Function name:' in stripped:
                    func_name = stripped.split('Function name:')[-1].strip()
                if func_name and func_name in agent_names and func_name not in seen_active:
                    seen_active.add(func_name)
                    aid, icon = agent_names[func_name]
                    yield send_event({"type": "trace", "agent": aid, "status": "active",
                        "msg": f"{icon} Manager delegated to {func_name}"})

                done_name = None
                if stripped.endswith('succeeded.') or stripped.endswith('succeeded'):
                    token = stripped.rsplit(' succeeded', 1)[0].strip()
                    if token.startswith('Function '):
                        token = token[len('Function '):].strip()
                    done_name = token
                if done_name:
                    if done_name in agent_names and done_name not in seen_done:
                        seen_done.add(done_name)
                        aid, icon = agent_names[done_name]
                        yield send_event({"type": "trace", "agent": aid, "status": "done",
                            "msg": f"{icon} {done_name} completed"})
                    elif done_name == 'get_products' and 'get_products' not in seen_done:
                        seen_done.add('get_products')
                        yield send_event({"type": "trace", "agent": "product", "status": "done",
                            "msg": "📦 get_products returned data"})
            except queue.Empty:
                break

        af_logger.removeHandler(handler)
        elapsed = time.time() - start

        # Phase 4: Post-execution trace — mark pipeline done in order
        if not seen_active:
            yield send_event({"type": "trace", "agent": "manager", "status": "done",
                "msg": "🧠 Manager handled directly (no sub-agent delegation)"})

        yield send_event({"type": "trace", "agent": "manager", "status": "done",
            "msg": f"🧠 ProductManagerAgent finished ({elapsed:.1f}s)"})
        yield send_event({"type": "trace", "agent": "server", "status": "done",
            "msg": "🌐 A2A Server → TaskArtifactUpdateEvent sent"})
        await asyncio.sleep(0.05)
        yield send_event({"type": "trace", "agent": "client", "status": "done",
            "msg": "📡 A2A Client received response"})
        await asyncio.sleep(0.05)
        yield send_event({"type": "trace", "agent": "user", "status": "done",
            "msg": "✅ Response delivered to user"})

        # Phase 5: Final response
        if 'error' in error_holder:
            yield send_event({"type": "response", "response": f"Error: {error_holder['error']}",
                "session_id": session_id, "is_complete": False, "requires_input": True})
        else:
            resp = result_holder.get('response', {})
            yield send_event({"type": "response",
                "response": resp.get('content', 'No response available'),
                "session_id": session_id,
                "is_complete": resp.get('is_task_complete', False),
                "requires_input": resp.get('require_user_input', True)})

        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive",
                 "X-Accel-Buffering": "no"})


@router.post("/message", response_model=ChatResponse)
async def send_message(chat_message: ChatMessage):
    """Fallback synchronous endpoint"""
    try:
        session_id = chat_message.session_id or str(uuid.uuid4())
        active_sessions[session_id] = session_id
        response = await product_management_agent.invoke(chat_message.message, session_id)
        return ChatResponse(
            response=response.get('content', 'No response available'),
            session_id=session_id,
            is_complete=response.get('is_task_complete', False),
            requires_input=response.get('require_user_input', True),
        )
        
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def stream_message(chat_message: ChatMessage):
    """Stream a response from the product management agent"""
    try:
        # Generate session ID if not provided
        session_id = chat_message.session_id or str(uuid.uuid4())
        
        # Store session
        active_sessions[session_id] = session_id
        
        async def generate_response():
            """Generate streaming response"""
            try:
                async for partial in product_management_agent.stream(
                    chat_message.message, session_id
                ):
                    # Format as SSE (Server-Sent Events)
                    content = partial.get('content', '')
                    is_complete = partial.get('is_task_complete', False)
                    requires_input = partial.get('require_user_input', False)
                    
                    response_data = {
                        "content": content,
                        "session_id": session_id,
                        "is_complete": is_complete,
                        "requires_input": requires_input
                    }
                    
                    yield f"data: {response_data}\n\n"
                    
                    if is_complete:
                        break
                        
            except Exception as e:
                logger.error(f"Error in streaming response: {e}")
                yield f'data: { {"error": "{str(e)}"} }\n\n'
        
        return StreamingResponse(
            generate_response(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*"
            }
        )
        
    except Exception as e:
        logger.error(f"Error setting up streaming: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def get_active_sessions():
    """Get list of active chat sessions"""
    return {"active_sessions": list(active_sessions.keys())}


@router.delete("/sessions/{session_id}")
async def clear_session(session_id: str):
    """Clear a specific chat session"""
    if session_id in active_sessions:
        del active_sessions[session_id]
        return {"message": f"Session {session_id} cleared"}
    else:
        raise HTTPException(status_code=404, detail="Session not found")


