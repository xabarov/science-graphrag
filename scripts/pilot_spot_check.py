#!/usr/bin/env python3
"""Wave D: automated structural spot-check for N POST /v1/query calls.

Validates each response has citations with work_id + chunk_fingerprint when hits exist.
Usage: BASE=http://127.0.0.1:8787 .venv/bin/python scripts/pilot_spot_check.py

Paste JSON output into docs/pilot/wave-d-exit-record.md (Citation spot-check section).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


def _post_query(base: str, query: str, top_k: int = 5) -> dict:
    body = json.dumps({"query": query, "top_k": top_k}).encode("utf-8")
    req = urllib.request.Request(  # noqa: S310
        f"{base.rstrip('/')}/v1/query",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _check_one(query: str, payload: dict) -> dict:
    """Return per-query structural check result."""
    cites = payload.get("citations") or []
    rt = payload.get("retrieval_trace") or {}
    hit_count = int(rt.get("hit_count") or 0)
    ok = True
    issues: list[str] = []
    warnings: list[str] = []
    if hit_count > 0 and len(cites) == 0:
        ok = False
        issues.append("hits_expected_but_no_citations")
    for i, c in enumerate(cites):
        if not c.get("work_id"):
            ok = False
            issues.append(f"citation_{i}_missing_work_id")
        # Prefer chunk_fingerprint; older ingest may only have document_id + rank.
        if not c.get("chunk_fingerprint") and not c.get("document_id"):
            ok = False
            issues.append(f"citation_{i}_missing_chunk_fingerprint_and_document_id")
        elif not c.get("chunk_fingerprint"):
            warnings.append(f"citation_{i}_legacy_no_chunk_fingerprint")
    synth = (rt.get("answer_synthesis") or {}).get("second_stage_llm")
    if synth is not None and synth is not False:
        ok = False
        issues.append("expected_answer_synthesis.second_stage_llm_false")
    return {
        "query": query,
        "ok": ok,
        "citation_count": len(cites),
        "hit_count": hit_count,
        "issues": issues,
        "warnings": warnings,
    }


def main() -> int:
    """Run fixed-query spot-check; exit 0 iff all structural checks pass."""

    base = os.environ.get("BASE", "http://127.0.0.1:8787")
    queries = [
        "How does YOLOv1 frame object detection as regression?",
        "How does Mask R-CNN extend Faster R-CNN for instance segmentation?",
        "What is focal loss in RetinaNet?",
        "How does DETR use transformers for object detection?",
        "What is the role of anchor boxes in Faster R-CNN?",
    ]
    rows: list[dict] = []
    all_ok = True
    for q in queries:
        try:
            payload = _post_query(base, q, top_k=5)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            rows.append({"query": q, "ok": False, "error": str(e)})
            all_ok = False
            continue
        row = _check_one(q, payload)
        rows.append(row)
        if not row["ok"]:
            all_ok = False

    out = {
        "base": base,
        "queries_run": len(queries),
        "all_structural_checks_passed": all_ok,
        "results": rows,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
