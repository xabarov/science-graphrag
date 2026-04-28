"""Canonical ingest job progress / UX phase (single source for API + SSE + UI)."""

from __future__ import annotations

from typing import Any

from science_graphrag.ingestion.stage_context import IngestStage
from science_graphrag.ingestion.stage_stats import (
    compute_weighted_progress_pct_with_running_fraction,
)

# Ordered UX phases (matches workspace strip).
INGEST_UX_PHASE_KEYS: tuple[str, ...] = (
    "preparing_document",
    "building_graph",
    "preparing_search",
    "finalizing",
)

# Map technical IngestStage id -> compact UX phase key.
STAGE_TO_UX_PHASE: dict[str, str] = {
    IngestStage.PARSE_PDF.value: "preparing_document",
    IngestStage.EXTRACT_META.value: "preparing_document",
    IngestStage.ENRICH_OPENALEX.value: "building_graph",
    IngestStage.ENRICH_ROR.value: "building_graph",
    IngestStage.WRITE_GRAPH.value: "building_graph",
    IngestStage.RESOLVE_REFERENCES.value: "building_graph",
    IngestStage.CHUNK.value: "preparing_search",
    IngestStage.EXTRACT_CLAIMS.value: "preparing_search",
    IngestStage.EMBED.value: "preparing_search",
    IngestStage.ATTACH_WORKSPACE.value: "finalizing",
}


def ux_phase_for_stage(stage_id: str) -> str:
    """Map a technical ingest stage id to a compact UX phase key."""
    sid = str(stage_id or "").strip()
    if not sid:
        return "preparing_document"
    return STAGE_TO_UX_PHASE.get(sid, "preparing_document")


def pick_active_stage_row(stages: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Prefer running row, else last failed, else last row (same semantics as compact strip)."""
    if not stages:
        return None
    for row in stages:
        if str(row.get("status") or "").strip().lower() == "running":
            return row
    for i in range(len(stages) - 1, -1, -1):
        st = stages[i]
        if str(st.get("status") or "").strip().lower() == "failed":
            return st
    return stages[-1]


def _progress_indeterminate(active: dict[str, Any] | None, *, job_status: str) -> bool:  # pylint: disable=too-many-return-statements
    """True when a single VL batch is in flight (no meaningful page fraction until HTTP returns)."""
    if str(job_status or "").strip().lower() != "running":
        return False
    if not active:
        return False
    if str(active.get("name") or "").strip() != IngestStage.PARSE_PDF.value:
        return False
    if str(active.get("status") or "").strip().lower() != "running":
        return False
    met = active.get("metrics") if isinstance(active.get("metrics"), dict) else {}
    try:
        batch_total = int(met.get("vl_batch_total") or 0)
    except (TypeError, ValueError):
        batch_total = 0
    if batch_total != 1:
        return False
    try:
        cur = (
            int(active.get("subprogress_current"))
            if active.get("subprogress_current") is not None
            else -1
        )
        tot = (
            int(active.get("subprogress_total"))
            if active.get("subprogress_total") is not None
            else 0
        )
    except (TypeError, ValueError):
        return False
    return tot > 0 and 0 <= cur < tot


def _running_intra_fraction(active: dict[str, Any] | None) -> float | None:
    if not active:
        return None
    if str(active.get("status") or "").strip().lower() != "running":
        return None
    tot = active.get("subprogress_total")
    cur = active.get("subprogress_current")
    if tot is None or cur is None:
        return None
    try:
        t = int(tot)
        c = int(cur)
    except (TypeError, ValueError):
        return None
    if t <= 0 or c < 0:
        return None
    return max(0.0, min(1.0, float(c) / float(t)))


def _legacy_boot_progress_pct(
    *, status: str, progress_current: int, progress_total: int
) -> float | None:
    """When no stage rows exist yet, map coarse worker progress to a small 0..1 range."""
    st = str(status or "").strip().lower()
    if st == "queued":
        return 0.0
    if st != "running":
        return None
    tot = max(int(progress_total or 100), 1)
    cur = max(0, min(100, int(progress_current or 0)))
    return max(0.0, min(0.12, float(cur) / float(tot) * 0.12))


def canonical_progress_fields_for_job(
    *,
    kind: str,
    status: str,
    message: str,
    progress_current: int,
    progress_total: int,
    stages: list[dict[str, Any]],
    weights: dict[str, int],
) -> dict[str, Any]:
    """
    Return flat fields merged into ingest job JSON:
    ingest_phase, active_stage, detail_message, subprogress_*, progress_pct (refined).
    """
    stage_rows = [dict(x) for x in stages]
    active = pick_active_stage_row(stage_rows)
    active_stage = str(active.get("name") or "").strip() if active else ""
    ingest_phase = ux_phase_for_stage(active_stage) if active_stage else "preparing_document"
    detail_message: str | None = None
    sub_c: int | None = None
    sub_t: int | None = None
    if active:
        dm = active.get("detail_message")
        if dm is not None and str(dm).strip():
            detail_message = str(dm).strip()[:500]
        try:
            if active.get("subprogress_total") is not None:
                sub_t = int(active["subprogress_total"])
        except (TypeError, ValueError):
            sub_t = None
        try:
            if active.get("subprogress_current") is not None:
                sub_c = int(active["subprogress_current"])
        except (TypeError, ValueError):
            sub_c = None

    intra = _running_intra_fraction(active)
    pct: float | None = None
    if kind in ("single", "batch_child") and stage_rows:
        pct = compute_weighted_progress_pct_with_running_fraction(
            stage_rows, weights, running_intra_fraction=intra
        )
    if pct is None and kind in ("single", "batch_child"):
        pct = _legacy_boot_progress_pct(
            status=status,
            progress_current=progress_current,
            progress_total=progress_total,
        )

    if not active_stage and str(status or "").strip().lower() in ("queued", "running"):
        if str(message or "").strip():
            detail_message = detail_message or str(message).strip()[:500]

    out: dict[str, Any] = {
        "ingest_phase": ingest_phase,
        "active_stage": active_stage,
        "detail_message": detail_message,
        "subprogress_current": sub_c,
        "subprogress_total": sub_t,
        "progress_indeterminate": _progress_indeterminate(active, job_status=str(status or "")),
    }
    if pct is not None:
        out["progress_pct"] = float(pct)
    return out


_TERMINAL_CHILD_STATUSES = frozenset({"completed", "failed"})


def _child_done_for_batch(ch: dict[str, Any]) -> bool:
    return str(ch.get("status") or "").lower() in _TERMINAL_CHILD_STATUSES


def _batch_child_dicts(parent: dict[str, Any]) -> list[dict[str, Any]]:
    raw = parent.get("child_jobs")
    if not isinstance(raw, list):
        return []
    return [ch for ch in raw if isinstance(ch, dict)]


def _batch_parent_progress_fraction(children: list[dict[str, Any]]) -> float:
    pcts: list[float] = []
    for ch in children:
        p = ch.get("progress_pct")
        if isinstance(p, (int, float)):
            pcts.append(max(0.0, min(1.0, float(p))))
    total = len(children)
    done = sum(1 for ch in children if _child_done_for_batch(ch))
    if pcts and len(pcts) == total:
        return sum(pcts) / float(total)
    if total > 0:
        return max(0.0, min(1.0, float(done) / float(total)))
    return 0.0


def _pick_active_batch_child(children: list[dict[str, Any]]) -> dict[str, Any] | None:
    for want in ("running", "queued"):
        for ch in children:
            if str(ch.get("status") or "").lower() == want:
                return ch
    return None


def apply_batch_parent_aggregates(parent: dict[str, Any]) -> None:
    """Mutate parent job dict: progress_pct, phase, active child strip fields."""
    children = _batch_child_dicts(parent)
    if not children:
        return

    parent["progress_pct"] = _batch_parent_progress_fraction(children)
    done = sum(1 for ch in children if _child_done_for_batch(ch))
    total = len(children)

    active_child = _pick_active_batch_child(children)
    if active_child:
        parent["ingest_phase"] = active_child.get("ingest_phase") or "preparing_document"
        parent["active_stage"] = active_child.get("active_stage") or ""
        parent["detail_message"] = active_child.get("detail_message")
        parent["subprogress_current"] = active_child.get("subprogress_current")
        parent["subprogress_total"] = active_child.get("subprogress_total")
        fn = active_child.get("filename")
        if fn and not parent.get("detail_message"):
            parent["detail_message"] = str(fn)[:200]
        return

    parent["ingest_phase"] = "finalizing"
    parent["active_stage"] = ""
    if done == total and total:
        parent["detail_message"] = parent.get("message") or parent.get("detail_message")


__all__ = [
    "INGEST_UX_PHASE_KEYS",
    "STAGE_TO_UX_PHASE",
    "apply_batch_parent_aggregates",
    "canonical_progress_fields_for_job",
    "pick_active_stage_row",
    "ux_phase_for_stage",
]
