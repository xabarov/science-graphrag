"""HTTP API for server-side Ask session persistence (file-backed)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from science_graphrag.api.ask_sessions_store import AskSessionsFileStore, default_ask_sessions_store

router = APIRouter(tags=["ask-sessions"])

_store: AskSessionsFileStore | None = None


def get_ask_sessions_store() -> AskSessionsFileStore:
    """Process-wide singleton; tests may assign ``ask_sessions._store`` directly."""

    global _store  # pylint: disable=global-statement
    if _store is None:
        _store = default_ask_sessions_store()
    return _store


class CreateSessionBody(BaseModel):
    scope: str = Field(..., min_length=1, max_length=256)
    title: str | None = Field(default=None, max_length=200)


class PatchSessionBody(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    turns: list[dict[str, Any]] | None = None
    active: bool | None = None


@router.get("/ask-sessions")
def list_ask_sessions(
    scope: str = Query(..., min_length=1, max_length=256),
) -> dict[str, Any]:
    try:
        return get_ask_sessions_store().list_sessions(scope)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid_scope") from None


@router.post("/ask-sessions")
def create_ask_session(body: CreateSessionBody) -> dict[str, Any]:
    try:
        row = get_ask_sessions_store().create_session(body.scope, body.title)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid_scope") from None
    return {"session": row}


@router.patch("/ask-sessions/{session_id}")
def patch_ask_session(
    session_id: str,
    body: PatchSessionBody,
    scope: str = Query(..., min_length=1, max_length=256),
) -> dict[str, Any]:
    try:
        row = get_ask_sessions_store().patch_session(
            scope,
            session_id,
            title=body.title,
            turns=body.turns,
            make_active=bool(body.active),
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid_scope") from None
    if not row:
        raise HTTPException(status_code=404, detail="session_not_found")
    return {"session": row}


@router.delete("/ask-sessions/{session_id}")
def delete_ask_session(
    session_id: str,
    scope: str = Query(..., min_length=1, max_length=256),
) -> dict[str, str]:
    try:
        ok = get_ask_sessions_store().delete_session(scope, session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid_scope") from None
    if not ok:
        raise HTTPException(status_code=404, detail="session_not_found")
    return {"status": "deleted"}
