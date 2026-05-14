"""Benchmark UI HTTP router (split implementation under this package)."""

from __future__ import annotations

from fastapi import APIRouter

from science_graphrag.api.task_store import task_store

# isort: split
from science_graphrag.api.benchmark.routes_catalog import router as catalog_router
from science_graphrag.api.benchmark.routes_runs import router as runs_router

# ``task_store`` must be bound on this package before route modules finish importing
# (defensive; ``runtime.task_store()`` resolves it only at HTTP call time).

router = APIRouter()
router.include_router(catalog_router)
router.include_router(runs_router)

__all__ = ["router", "task_store"]
