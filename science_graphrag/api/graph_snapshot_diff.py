"""Graph CLI JSON vs gold ``graph_expectations`` (server-side, mirrors UI compare)."""

from __future__ import annotations

import math
from typing import Any


def _num(val: Any) -> float | None:
    if val is None or val == "":
        return None
    try:
        n = float(val)
    except (TypeError, ValueError):
        return None
    return n if math.isfinite(n) else None


def extract_metrics_snapshot(parsed: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return ``metrics.snapshot`` from CLI-shaped JSON (supports ``case.metrics`` root)."""
    if not parsed or not isinstance(parsed, dict):
        return None
    inner = parsed.get("case")
    metrics = None
    if isinstance(inner, dict):
        metrics = inner.get("metrics")
    if metrics is None:
        metrics = parsed.get("metrics")
    if not isinstance(metrics, dict):
        return None
    snap = metrics.get("snapshot")
    return snap if isinstance(snap, dict) else None


def snapshot_case_id(parsed: dict[str, Any] | None) -> str | None:
    """Resolve ``case_id`` from CLI-shaped snapshot JSON."""
    if not parsed or not isinstance(parsed, dict):
        return None
    inner = parsed.get("case")
    if isinstance(inner, dict) and inner.get("case_id") is not None:
        return str(inner["case_id"])
    if parsed.get("case_id") is not None:
        return str(parsed["case_id"])
    return None


def compare_graph_expectations_to_snapshot(  # pylint: disable=too-many-locals
    expectations: dict[str, Any] | None,
    snapshot: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build diff rows and arxiv notes (same semantics as ``graphSnapshotCompare.js``)."""
    rows: list[dict[str, Any]] = []
    arxiv_notes: list[str] = []

    if not expectations or not isinstance(expectations, dict):
        return {"rows": rows, "arxiv_notes": ["No graph_expectations in gold."]}
    if not snapshot or not isinstance(snapshot, dict):
        return {
            "rows": rows,
            "arxiv_notes": [
                "No metrics.snapshot in payload (expected graph benchmark JSON).",
            ],
        }

    exp = expectations
    snap = snapshot

    def add_range(label: str, snap_val: Any, min_key: str, max_key: str) -> None:
        v = _num(snap_val)
        if v is None:
            return
        min_c = _num(exp.get(min_key))
        max_c = _num(exp.get(max_key))
        if min_c is None and max_c is None:
            return
        ok = (min_c is None or v >= min_c) and (max_c is None or v <= max_c)
        lo = min_c if min_c is not None else "—"
        hi = max_c if max_c is not None else "—"
        rows.append(
            {
                "field": label,
                "snapshot": str(int(v) if v == int(v) else v),
                "expected": f"{lo} … {hi}",
                "ok": ok,
            }
        )

    add_range("cites_count", snap.get("cites_count"), "min_cites", "max_cites")
    add_range(
        "authorship_count", snap.get("authorship_count"), "min_authorships", "max_authorships"
    )
    add_range(
        "institution_count", snap.get("institution_count"), "min_institutions", "max_institutions"
    )

    dups = _num(snap.get("duplicate_work_fingerprints"))
    max_d = _num(exp.get("max_duplicate_work_fingerprints"))
    if dups is not None and max_d is not None:
        ok = dups <= max_d
        rows.append(
            {
                "field": "duplicate_work_fingerprints",
                "snapshot": str(int(dups) if dups == int(dups) else dups),
                "expected": f"≤ {max_d}",
                "ok": ok,
            }
        )

    max_viol = _num(exp.get("max_work_dedup_violations"))
    viol_raw = snap.get("work_dedup_violations")
    if viol_raw is None:
        viol_raw = snap.get("work_dedup_violation_count")
    viol = _num(viol_raw)
    if viol is not None and max_viol is not None:
        rows.append(
            {
                "field": "work_dedup_violations",
                "snapshot": str(int(viol) if viol == int(viol) else viol),
                "expected": f"≤ {max_viol}",
                "ok": viol <= max_viol,
            }
        )

    expected_arxiv = (
        [str(x) for x in exp["expected_cited_arxiv_ids"]]
        if isinstance(exp.get("expected_cited_arxiv_ids"), list)
        else []
    )
    actual_arxiv = (
        [str(x) for x in snap["cited_arxiv_ids"]]
        if isinstance(snap.get("cited_arxiv_ids"), list)
        else []
    )

    if expected_arxiv or actual_arxiv:
        exp_set = set(expected_arxiv)
        act_set = set(actual_arxiv)
        missing = [i for i in expected_arxiv if i not in act_set]
        extra = [i for i in actual_arxiv if i not in exp_set]
        arxiv_notes.append(
            f"Expected arxiv ids: {len(expected_arxiv)}, snapshot cites: {len(actual_arxiv)}",
        )
        if missing:
            tail = ", ".join(missing[:12])
            if len(missing) > 12:
                tail += "…"
            arxiv_notes.append(f"Missing in snapshot ({len(missing)}): {tail}")
        if extra:
            tail = ", ".join(extra[:12])
            if len(extra) > 12:
                tail += "…"
            arxiv_notes.append(f"Extra in snapshot ({len(extra)}): {tail}")
        if not missing and not extra and expected_arxiv:
            arxiv_notes.append("cited_arxiv_ids set matches expected_cited_arxiv_ids.")

    return {"rows": rows, "arxiv_notes": arxiv_notes}
