"""Ingestion package. Public ``ingest_document`` is a thin lazy wrapper (avoids import cycles)."""

from __future__ import annotations

from typing import Any


def ingest_document(*args: Any, **kwargs: Any) -> Any:
    """Delegate to the full pipeline (imported on first call)."""

    from science_graphrag.ingestion.pipeline import ingest_document as _ingest_document

    return _ingest_document(*args, **kwargs)


__all__ = ["ingest_document"]
