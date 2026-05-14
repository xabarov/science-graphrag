"""Postgres + Neo4j workspace helpers for OD workspace E2E audit."""

from __future__ import annotations

from typing import Any

from sqlalchemy import create_engine, text


def postgres_workspace_ingest_counts(database_url: str, workspace_id: str) -> dict[str, Any]:
    engine = create_engine(database_url, pool_pre_ping=True)
    out: dict[str, Any] = {"ingest_jobs_total": None, "ingest_jobs_completed": None, "error": None}
    try:
        with engine.connect() as conn:
            r = conn.execute(
                text(
                    "SELECT COUNT(*) FROM ingest_jobs WHERE workspace_id = :wid",
                ),
                {"wid": workspace_id},
            )
            out["ingest_jobs_total"] = int(r.scalar() or 0)
            r2 = conn.execute(
                text(
                    "SELECT COUNT(*) FROM ingest_jobs WHERE workspace_id = :wid AND status = :st",
                ),
                {"wid": workspace_id, "st": "completed"},
            )
            out["ingest_jobs_completed"] = int(r2.scalar() or 0)
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        engine.dispose()
    return out


def pick_workspace(
    workspaces: list[dict[str, Any]],
    *,
    needle: str,
    min_works: int,
) -> dict[str, Any] | None:
    n = (needle or "").strip().lower()
    candidates = [
        w
        for w in workspaces
        if n in (w.get("name") or "").lower() and len(w.get("work_ids") or []) >= min_works
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda w: len(w.get("work_ids") or []))
