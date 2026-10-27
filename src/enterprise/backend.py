import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field

from enterprise.config import DOCUMENTS, INDEX, ROOT
from enterprise.models import ChatRequest, StrictModel
from enterprise.orchestrator import Copilot
from enterprise.rag import Retrieval, ingest
from enterprise.registry import Registry, ToolFailure

logging.basicConfig(level=logging.INFO, format="%(message)s")


@asynccontextmanager
async def lifespan(app):
    registry = await Registry().connect()
    app.state.copilot = Copilot(registry, Retrieval(ingest(DOCUMENTS, INDEX)))
    yield
    await registry.close()


app = FastAPI(title="Enterprise Operations Copilot", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=ROOT / "apps/frontend"), name="static")


@app.get("/")
def home():
    return FileResponse(ROOT / "apps/frontend/index.html")


@app.get("/health")
def health():
    r = app.state.copilot.registry
    return {
        "status": "ok" if len(r.sessions) == 2 else "degraded",
        "servers": list(r.sessions),
        "tools": len(r.tools),
        "unavailable": r.unavailable,
    }


@app.get("/api/tools")
def tools():
    return {
        "tools": app.state.copilot.registry.catalog(),
        "unavailable": app.state.copilot.registry.unavailable,
    }


@app.post("/api/chat")
async def chat(request: ChatRequest):
    return await app.state.copilot.run(
        request.message, request.conversation_id, request.degraded_demo
    )


class Confirmation(StrictModel):
    draft_id: str = Field(min_length=1, max_length=64)
    conversation_id: str = Field(min_length=1, max_length=64)
    confirmed: bool = False


@app.post("/api/tickets/confirm")
async def confirm(request: Confirmation):
    try:
        return await app.state.copilot.confirm(
            request.draft_id, request.conversation_id, request.confirmed
        )
    except ToolFailure as exc:
        raise HTTPException(400, str(exc)) from exc
