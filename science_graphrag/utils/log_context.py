"""Ingest-scoped logging context (correlation IDs only; no document text or secrets).

Use ``ingest_log_context`` around ingest worker / actor execution so stderr logs
from ``science_graphrag.*`` include ``job_id`` / ``workspace_id`` via the handler
filter in ``project_logging``.

**Canonical ``extra=`` keys** for explicit ``Logger.info(..., extra=...)`` when
context propagation is unavailable: ``job_id``, ``workspace_id``, ``stage``
(short enum-like string, e.g. ``actor_pipeline``, ``worker_start``).
"""

from __future__ import annotations

import contextvars
from collections.abc import Iterator
from contextlib import contextmanager

_ingest_job_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "science_graphrag_ingest_job_id", default=None
)
_ingest_workspace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "science_graphrag_ingest_workspace_id", default=None
)


def get_ingest_job_id() -> str | None:
    """Bound ingest job id for the current context, if any."""
    return _ingest_job_id.get()


def get_ingest_workspace_id() -> str | None:
    """Bound workspace id for the current context, if any."""
    return _ingest_workspace_id.get()


@contextmanager
def ingest_log_context(
    *,
    job_id: str | None = None,
    workspace_id: str | None = None,
) -> Iterator[None]:
    """Bind ``job_id`` / ``workspace_id`` for logging for the duration of the block."""
    token_job = _ingest_job_id.set(job_id)
    token_ws = _ingest_workspace_id.set(workspace_id)
    try:
        yield
    finally:
        _ingest_job_id.reset(token_job)
        _ingest_workspace_id.reset(token_ws)
