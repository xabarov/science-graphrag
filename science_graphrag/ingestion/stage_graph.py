"""Typed runtime state for ingest_document stage graph."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from science_graphrag.config import Settings
from science_graphrag.storage.models_orm import DocumentRecord


@dataclass(slots=True)
class IngestDocumentRuntimeState:
    """Mutable runtime state shared across ingest stages."""

    settings: Settings
    document_id: str
    sha256: str
    reused_document: bool
    workspace_id: str | None
    checkpoint: dict[str, Any]
    progress_emit: Any | None
    ingest_workspace_ids: list[str] | None


def build_runtime_state(
    *,
    settings: Settings,
    document_id: str,
    sha256: str,
    reused_document: bool,
    workspace_id: str | None,
    progress_emit: Any | None,
    ingest_workspace_ids: list[str] | None,
) -> IngestDocumentRuntimeState:
    """Create initial runtime state container."""
    return IngestDocumentRuntimeState(
        settings=settings,
        document_id=document_id,
        sha256=sha256,
        reused_document=reused_document,
        workspace_id=workspace_id,
        checkpoint={},
        progress_emit=progress_emit,
        ingest_workspace_ids=ingest_workspace_ids,
    )


def load_checkpoint_from_session(
    state: IngestDocumentRuntimeState,
    *,
    session: Any | None,
    parse_checkpoint,
    default_checkpoint,
) -> None:
    """Load existing checkpoint for reused document when present."""
    state.checkpoint = default_checkpoint()
    if session is None or not state.reused_document:
        return
    prev_doc = session.get(DocumentRecord, state.document_id)
    if prev_doc is not None and prev_doc.ingest_checkpoint_json:
        state.checkpoint = parse_checkpoint(prev_doc.ingest_checkpoint_json)
