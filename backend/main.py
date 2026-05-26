"""
AI Agent Platform & Sandbox — Orchestration & Visualization Platform
FastAPI server with SSE streaming, REST API, and static file serving.
"""

import asyncio
import json
import uuid
import time
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from backend.agent_engine import AgentEngine
from backend.context_manager import ContextManager
from backend.trace import TraceSystem
from backend.models import AgentRequest
from backend.tools import registry

# Initialize core systems
context_manager = ContextManager(max_tokens=4096)
trace_system = TraceSystem()
agent = AgentEngine(context_manager, trace_system)

# FastAPI app
app = FastAPI(
    title="AI Agent Platform & Sandbox",
    description="AI Agent Orchestration & Visualization Platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main frontend page."""
    index_path = FRONTEND_DIR / "index.html"
    return HTMLResponse(content=index_path.read_text(), status_code=200)


@app.post("/api/agent/stream")
async def agent_stream(request: AgentRequest):
    """Stream agent reasoning steps via Server-Sent Events."""
    conversation_id = request.conversation_id or str(uuid.uuid4())

    async def event_generator():
        try:
            async for step in agent.run(
                query=request.query,
                conversation_id=conversation_id,
                max_steps=request.max_steps,
                llm_config=request.llm_config,
            ):

                event_data = {
                    "conversation_id": conversation_id,
                    "step": {
                        "id": step.id,
                        "step_number": step.step_number,
                        "step_type": step.step_type.value,
                        "content": step.content,
                        "tool_call": step.tool_call.model_dump() if step.tool_call else None,
                        "tool_result": step.tool_result,
                        "latency_ms": step.latency_ms,
                        "tokens_used": step.tokens_used,
                        "timestamp": step.timestamp.isoformat(),
                    },
                }
                yield f"event: step\ndata: {json.dumps(event_data)}\n\n"
                await asyncio.sleep(0.3)  # Simulate streaming delay for visual effect

            # Send done event
            summary = trace_system.get_summary(conversation_id)
            yield f"event: done\ndata: {json.dumps({'conversation_id': conversation_id, 'summary': summary})}\n\n"

        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/tools")
async def list_tools():
    """List all available tool adapters."""
    tools = registry.list_tools()
    return JSONResponse(content=[
        {
            "name": t.name,
            "description": t.description,
            "category": t.category,
            "parameters": [p.model_dump() for p in t.parameters],
            "examples": t.examples,
        }
        for t in tools
    ])


@app.get("/api/traces/{conversation_id}")
async def get_traces(conversation_id: str):
    """Get execution traces for a conversation."""
    traces = trace_system.get_traces(conversation_id)
    waterfall = trace_system.get_waterfall(conversation_id)
    summary = trace_system.get_summary(conversation_id)
    return JSONResponse(content={
        "traces": traces,
        "waterfall": waterfall,
        "summary": summary,
    })


@app.get("/api/traces/{conversation_id}/export")
async def export_traces(conversation_id: str):
    """Export traces as JSON."""
    return JSONResponse(
        content=json.loads(trace_system.export_json(conversation_id)),
        headers={"Content-Disposition": f"attachment; filename=trace_{conversation_id}.json"},
    )


@app.get("/api/context/{conversation_id}")
async def get_context(conversation_id: str):
    """Get context window state for a conversation."""
    stats = context_manager.get_stats(conversation_id)
    context = context_manager.get_context(conversation_id)
    return JSONResponse(content={"stats": stats, "messages": context})


@app.get("/api/conversations")
async def list_conversations():
    """List all active conversations."""
    return JSONResponse(content=context_manager.list_conversations())


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "tools_loaded": len(registry.list_tools())}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
