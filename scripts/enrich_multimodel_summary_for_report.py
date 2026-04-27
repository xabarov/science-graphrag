#!/usr/bin/env python3
"""Attach extraction / graph snapshot metrics to multimodel summary rows (report helper).

Reads ``eval/results/multimodel/summary.json`` and merges in macro metrics from:
  - ``eval/results/extraction-entity-metrics-for-report.json`` (slot table)
  - ``eval/results/graph-cites-for-report.json`` (Neo4j CITES vs gold)
  - ``eval/results/relations-graph-for-report.json`` (semantic Method/Dataset)
  - ``eval/results/claims-paraphrase-diagnostics-for-report.json`` (optional)

Writes ``eval/results/multimodel/summary-for-report.json`` (does not overwrite ``summary.json``).

Latency/cost: not available from committed artifacts; rows get ``latency_cost_note`` placeholder.

Usage::

  .venv/bin/python scripts/enrich_multimodel_summary_for_report.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from benchmark_aggregator.paths import ROOT  # noqa: E402


def _resolve(repo: Path, p: str) -> Path:
    path = Path(p)
    return path if path.is_absolute() else (repo / path).resolve()


def _slot_mm(slots: list[dict[str, Any]], slot_id: str) -> dict[str, Any] | None:
    for s in slots:
        if s.get("slot_id") == slot_id:
            return s.get("macro_mean") if isinstance(s.get("macro_mean"), dict) else None
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument(
        "--multimodel-summary",
        type=str,
        default="eval/results/multimodel/summary.json",
    )
    parser.add_argument(
        "--extraction-report",
        type=str,
        default="eval/results/extraction-entity-metrics-for-report.json",
    )
    parser.add_argument(
        "--graph-cites-report",
        type=str,
        default="eval/results/graph-cites-for-report.json",
    )
    parser.add_argument(
        "--relations-report",
        type=str,
        default="eval/results/relations-graph-for-report.json",
    )
    parser.add_argument(
        "--claims-diagnostics",
        type=str,
        default="eval/results/claims-paraphrase-diagnostics-for-report.json",
    )
    parser.add_argument(
        "--out-json",
        type=str,
        default="eval/results/multimodel/summary-for-report.json",
    )
    args = parser.parse_args(argv)
    repo = args.repo_root.resolve()
    sum_path = _resolve(repo, args.multimodel_summary)
    if not sum_path.is_file():
        print(f"Missing {sum_path}", file=sys.stderr)
        return 1
    summary = json.loads(sum_path.read_text(encoding="utf-8"))
    slots: list[dict[str, Any]] = []
    ext_path = _resolve(repo, args.extraction_report)
    if ext_path.is_file():
        ext = json.loads(ext_path.read_text(encoding="utf-8"))
        slots = ext.get("slots") or []
    graph_mm: dict[str, Any] = {}
    gp = _resolve(repo, args.graph_cites_report)
    if gp.is_file():
        g = json.loads(gp.read_text(encoding="utf-8"))
        graph_mm = g.get("macro_mean") or {}
    rel_mm: dict[str, Any] = {}
    rel_src = ""
    rp = _resolve(repo, args.relations_report)
    if rp.is_file():
        r = json.loads(rp.read_text(encoding="utf-8"))
        rel_mm = r.get("macro_mean") or {}
        rel_src = str(r.get("source_label") or "")
    claims_diag: dict[str, Any] | None = None
    cp = _resolve(repo, args.claims_diagnostics)
    if cp.is_file():
        claims_diag = json.loads(cp.read_text(encoding="utf-8"))

    def _pick(slot_id: str) -> dict[str, Any]:
        mm = _slot_mm(slots, slot_id)
        return mm or {}

    snap = {
        "methods_macro_f1": _pick("methods").get("f1"),
        "datasets_macro_f1": _pick("datasets").get("f1"),
        "claims_paraphrase_pilot_macro_f1": _pick("claims_paraphrase_pilot").get("f1"),
        "claims_paraphrase_holdout_macro_f1": _pick("claims_paraphrase_holdout").get("f1"),
        "concept_topic_concepts_macro_f1": _pick("concept_topic_concepts").get("f1"),
        "concept_topic_topics_macro_f1": _pick("concept_topic_topics").get("f1"),
        "references_resolution_mini_macro_f1": _pick("references_resolution_mini").get("f1"),
        "graph_cites_macro": graph_mm,
        "semantic_relations_macro": {**rel_mm, "source_label": rel_src},
        "claims_paraphrase_diagnostics": claims_diag,
        "latency_cost_note": (
            "Latency and USD cost per suite are not in committed JSON; "
            "collect from Phoenix / OpenRouter usage logs when comparing models."
        ),
    }

    rows = summary.get("rows") or []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            model = str(row.get("extraction_llm_model") or row.get("model") or "")
            if not model:
                continue
            row["extraction_graph_snapshot"] = snap

    out = {
        **summary,
        "inputs": {
            "base_summary": str(sum_path),
            "extraction_report": str(ext_path) if ext_path.is_file() else None,
            "graph_cites_report": str(gp) if gp.is_file() else None,
            "relations_report": str(rp) if rp.is_file() else None,
            "claims_diagnostics": str(cp) if cp.is_file() else None,
        },
        "rows": rows,
    }
    out_path = _resolve(repo, args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
