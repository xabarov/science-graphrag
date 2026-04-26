"""FastAPI entrypoint: retrieval, citations, minimal researcher UI."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import Depends, FastAPI, Query
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from qdrant_client import QdrantClient

from science_graphrag.agent.context.session_backend import configure_session_memory_backend
from science_graphrag.api.admin_access import require_admin_if_configured
from science_graphrag.api.agent import router as agent_router
from science_graphrag.api.agent_v2 import router as agent_v2_router
from science_graphrag.api.ask_sessions import router as ask_sessions_router
from science_graphrag.api.benchmark import router as benchmark_router
from science_graphrag.api.benchmark_decision_gate import router as benchmark_decision_gate_router
from science_graphrag.api.deps import (
    StoreRegistry,
    close_store_registry,
    get_stores,
    init_store_registry,
)
from science_graphrag.api.entity_dedup import router as entity_dedup_router
from science_graphrag.api.idea_assist import router as idea_assist_router
from science_graphrag.api.ingest.registry import _registry
from science_graphrag.api.ingest_event_bus import BUS
from science_graphrag.api.ingest_jobs import router as ingest_router
from science_graphrag.api.retrieval import router as retrieval_router
from science_graphrag.api.settings import router as settings_router
from science_graphrag.api.translation import router as translation_router
from science_graphrag.api.works import works_router
from science_graphrag.api.workspace_dedup import router as workspace_dedup_router
from science_graphrag.api.workspace_graph import router as workspace_graph_router
from science_graphrag.api.workspaces import router as workspaces_router
from science_graphrag.config import get_settings
from science_graphrag.ingestion.embeddings import resolve_embedding_dim
from science_graphrag.observability.phoenix_tracer import init_tracer_provider
from science_graphrag.storage.qdrant_store import ensure_entity_dedup_collections


@asynccontextmanager
async def _app_lifespan(app: FastAPI):
    init_tracer_provider()
    BUS.attach_loop(asyncio.get_running_loop())
    settings = get_settings()
    configure_session_memory_backend(settings)
    _registry(settings).bootstrap()
    app.state.stores = init_store_registry(settings)
    _dim = resolve_embedding_dim(settings=settings)
    ensure_entity_dedup_collections(
        QdrantClient(url=settings.qdrant_url, check_compatibility=False),
        vector_dim=_dim,
    )
    try:
        yield
    finally:
        close_store_registry()


app = FastAPI(title="science-graphrag", version="0.1.0", lifespan=_app_lifespan)
_STATIC_DIR = Path(__file__).resolve().parent / "static"
# React/Vite build: `science_graphrag/api/static/ui/` → served at `/ui` (includes `/ui/assets/*`).
# Do not mount `/ui/assets` to `_STATIC_DIR`: hashed bundles live under `static/ui/assets/`.
_UI_DIR = _STATIC_DIR / "ui"
if _UI_DIR.is_dir():
    app.mount("/ui", StaticFiles(directory=_UI_DIR, html=True), name="ui")

# Benchmark endpoints (UI-driven runs + fixtures).
app.include_router(
    benchmark_router,
    prefix="/v1",
    dependencies=[Depends(require_admin_if_configured)],
)
app.include_router(
    benchmark_decision_gate_router,
    prefix="/v1",
    dependencies=[Depends(require_admin_if_configured)],
)
app.include_router(
    settings_router,
    prefix="/v1",
    dependencies=[Depends(require_admin_if_configured)],
)
app.include_router(ask_sessions_router, prefix="/v1")
app.include_router(entity_dedup_router, prefix="/v1")
app.include_router(workspaces_router, prefix="/v1")
app.include_router(workspace_graph_router)
app.include_router(workspace_dedup_router, prefix="/v1/workspaces")
app.include_router(ingest_router, prefix="/v1")
app.include_router(agent_router, prefix="/v1")
app.include_router(agent_v2_router, prefix="/v2")
app.include_router(idea_assist_router, prefix="/v1")
app.include_router(translation_router, prefix="/v1")
app.include_router(retrieval_router, prefix="/v1")
app.include_router(works_router)


def _configure_access_log_filters() -> None:
    class _SuppressIngestPolling(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
            msg = record.getMessage()
            if record.levelno != logging.INFO:
                return True
            return "/v1/ingest/jobs/" not in msg or '" 200' not in msg

    access_logger = logging.getLogger("uvicorn.access")
    if any(
        type(existing).__name__ == "_SuppressIngestPolling" for existing in access_logger.filters
    ):
        return
    access_logger.addFilter(_SuppressIngestPolling())


_configure_access_log_filters()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/idea-search")
def idea_search(
    q: str = Query("", min_length=0),
    kinds: str = Query("work,chunk", description="Comma-separated kinds."),
    top_k: int = Query(5, ge=1, le=24),
    workspace_id: str | None = Query(default=None),
    settings: Settings = Depends(get_settings),
    stores: StoreRegistry = Depends(get_stores),
) -> dict[str, Any]:
    from science_graphrag.agent.tools.idea_search import IdeaSearchTool

    kind_list = [k.strip() for k in (kinds or "").split(",") if k.strip()]
    tool = IdeaSearchTool(
        stores.qdrant_chunks,
        work_store=stores.qdrant_works,
        settings=settings,
    )
    res = tool.run(
        q=q,
        kinds=kind_list,
        workspace_id=(workspace_id or "").strip() or None,
        top_k=top_k,
    )
    return {
        "items": res.payload.get("items", []),
        "query": q,
        "kinds": kind_list,
        "top_k": top_k,
        "workspace_id": (workspace_id or "").strip() or None,
        "status": "ok",
    }


@app.get("/", response_model=None)
def root_page() -> RedirectResponse | HTMLResponse:
    if _UI_DIR.is_dir():
        return RedirectResponse(url="/ui/", status_code=307)
    return HTMLResponse(
        content="<p>UI missing; open science_graphrag/api/static/ui/index.html after building the frontend.</p>",
        status_code=200,
    )


@app.get("/legacy/retrieval-mvp", response_class=HTMLResponse, response_model=None)
def legacy_retrieval_mvp_page() -> FileResponse | HTMLResponse:
    index = _STATIC_DIR / "index.html"
    if index.is_file():
        return FileResponse(index)
    return HTMLResponse(
        content="<p>Legacy retrieval MVP missing; open science_graphrag/api/static/index.html in repo.</p>",
        status_code=200,
    )


def main() -> None:
    uvicorn.run(
        "science_graphrag.api.main:app",
        host="0.0.0.0",
        port=8787,
        reload=False,
    )
