#!/usr/bin/env python3
"""
Aggregate extraction-oriented metrics from benchmark suite JSONs into report-facing tables.

Reads Layer-1 / Layer-2 / claims-paraphrase / concept-topic / references-resolution
suite artifacts (defaults match ``scripts/benchmark_aggregator/paths.py``) and writes:
  - machine-readable JSON (macro-means over cases, skipping nulls);
  - a Markdown fragment suitable for pasting into the NLP report.

Usage (repo root):
  .venv/bin/python scripts/report_extraction_entity_metrics.py
  .venv/bin/python scripts/report_extraction_entity_metrics.py \\
    --layer1-json eval/results/current-llm-layer1-nightly-heavy-suite.json \\
    --out-json eval/results/extraction-entity-metrics-for-report.json \\
    --out-md eval/results/extraction-entity-metrics-for-report.md
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from benchmark_aggregator.paths import (  # noqa: E402
    DEFAULT_CLAIMS_PARAPHRASE_HOLDOUT,
    DEFAULT_CLAIMS_PARAPHRASE_PILOT,
    DEFAULT_CONCEPT_TOPIC_MINI_SUITE,
    DEFAULT_LAYER1_NIGHTLY,
    DEFAULT_LAYER2_NIGHTLY,
    DEFAULT_REFERENCES_RESOLUTION_MINI,
    ROOT,
)


def _mean_skip_none(values: Iterable[float | None]) -> float | None:
    xs = [float(x) for x in values if x is not None and not math.isnan(float(x))]
    if not xs:
        return None
    return sum(xs) / len(xs)


def _f1_from_pr(p: float | None, r: float | None) -> float | None:
    if p is None or r is None:
        return None
    if p + r <= 0.0:
        return 0.0
    return (2.0 * p * r) / (p + r)


def _read_suite_cases(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    cases = raw.get("cases")
    if not isinstance(cases, list):
        return raw, []
    return raw, cases


@dataclass
class SlotAgg:
    slot_id: str
    label: str
    metric_family: str
    values: dict[str, list[float | None]] = field(default_factory=dict)

    def add(self, key: str, value: float | None) -> None:
        self.values.setdefault(key, []).append(value)

    def to_row(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "slot_id": self.slot_id,
            "label": self.label,
            "metric_family": self.metric_family,
            "n_cases_with_value": {},
            "macro_mean": {},
        }
        for k, vs in self.values.items():
            present = [v for v in vs if v is not None]
            row["n_cases_with_value"][k] = len(present)
            row["macro_mean"][k] = _mean_skip_none(vs)
        return row


def build_layer1_aggs(cases: list[dict[str, Any]]) -> list[SlotAgg]:
    slots: list[SlotAgg] = [
        SlotAgg(
            "work_title_token_f1",
            "Work title ( multiset token F1 )",
            "similarity",
        ),
        SlotAgg("work_title_rouge_l", "Work title ( ROUGE-L F1 )", "similarity"),
        SlotAgg(
            "work_abstract_rouge_l",
            "Work abstract vs gold prefix ( ROUGE-L F1 )",
            "similarity",
        ),
        SlotAgg(
            "work_abstract_prefix_containment",
            "Work abstract ( token containment vs prefix )",
            "similarity",
        ),
        SlotAgg("author_names", "Author names ( multiset P/R/F1 )", "prf1"),
        SlotAgg("affiliations", "Affiliations ( multiset P/R/F1 )", "prf1"),
        SlotAgg(
            "references_sample_arxiv",
            "References — gold sample arXiv ids ( multiset P/R/F1 )",
            "prf1",
        ),
        SlotAgg(
            "references_sample_doi",
            "References — gold sample DOIs ( multiset P/R/F1 )",
            "prf1",
        ),
    ]
    by_id = {s.slot_id: s for s in slots}

    for case in cases:
        m = case.get("metrics") or {}
        meta = m.get("metadata") or {}
        auth = m.get("authorships") or {}
        refs = m.get("references") or {}

        by_id["work_title_token_f1"].add("score", meta.get("title_token_f1"))
        by_id["work_title_rouge_l"].add("score", meta.get("title_rouge_l"))
        by_id["work_abstract_rouge_l"].add("score", meta.get("abstract_rouge_l_vs_prefix"))
        by_id["work_abstract_prefix_containment"].add(
            "score", meta.get("abstract_prefix_containment")
        )

        by_id["author_names"].add("precision", auth.get("names_precision"))
        by_id["author_names"].add("recall", auth.get("names_recall"))
        by_id["author_names"].add("f1", auth.get("names_f1"))

        by_id["affiliations"].add("precision", auth.get("affiliations_precision"))
        by_id["affiliations"].add("recall", auth.get("affiliations_recall"))
        by_id["affiliations"].add("f1", auth.get("affiliations_f1"))

        by_id["references_sample_arxiv"].add("precision", refs.get("sample_arxiv_precision"))
        by_id["references_sample_arxiv"].add("recall", refs.get("sample_arxiv_recall"))
        by_id["references_sample_arxiv"].add("f1", refs.get("sample_arxiv_f1"))

        by_id["references_sample_doi"].add("precision", refs.get("sample_doi_precision"))
        by_id["references_sample_doi"].add("recall", refs.get("sample_doi_recall"))
        by_id["references_sample_doi"].add("f1", refs.get("sample_doi_f1"))

    return slots


def build_layer2_aggs(cases: list[dict[str, Any]]) -> list[SlotAgg]:
    methods = SlotAgg("methods", "Methods ( soft name/alias match P/R/F1 )", "prf1")
    datasets = SlotAgg("datasets", "Datasets ( soft name/alias match P/R/F1 )", "prf1")
    for case in cases:
        m = case.get("metrics") or {}
        pm = m.get("precision_methods")
        pd_ = m.get("precision_datasets")
        if m.get("recall_methods") is not None and m.get("methods_f1") is not None:
            rm = float(m["recall_methods"])
            mf = float(m["methods_f1"])
        else:
            rmn, rmd = m.get("recall_methods_num"), m.get("recall_methods_denom")
            try:
                rm = float(rmn) / float(rmd) if rmd not in (None, 0) else None
            except (TypeError, ValueError):
                rm = None
            mf = _f1_from_pr(float(pm) if pm is not None else None, rm)
        if m.get("recall_datasets") is not None and m.get("datasets_f1") is not None:
            rd = float(m["recall_datasets"])
            df = float(m["datasets_f1"])
        else:
            dsn, dsd = m.get("recall_datasets_num"), m.get("recall_datasets_denom")
            try:
                rd = float(dsn) / float(dsd) if dsd not in (None, 0) else None
            except (TypeError, ValueError):
                rd = None
            df = _f1_from_pr(float(pd_) if pd_ is not None else None, rd)
        methods.add("precision", float(pm) if pm is not None else None)
        methods.add("recall", rm)
        methods.add("f1", mf)
        datasets.add("precision", float(pd_) if pd_ is not None else None)
        datasets.add("recall", rd)
        datasets.add("f1", df)
    return [methods, datasets]


def build_concept_topic_aggs(cases: list[dict[str, Any]]) -> list[SlotAgg]:
    concepts = SlotAgg(
        "concept_topic_concepts",
        "Concept-topic mini — concepts ( multiset P/R/F1 )",
        "prf1",
    )
    topics = SlotAgg(
        "concept_topic_topics",
        "Concept-topic mini — research topics ( multiset P/R/F1 )",
        "prf1",
    )
    for case in cases:
        m = case.get("metrics") or {}
        cp = m.get("concept_precision")
        cr = m.get("concept_recall")
        cf = _f1_from_pr(float(cp) if cp is not None else None, float(cr) if cr is not None else None)
        tp = m.get("topic_precision")
        tr = m.get("topic_recall")
        tf = _f1_from_pr(float(tp) if tp is not None else None, float(tr) if tr is not None else None)
        concepts.add("precision", float(cp) if cp is not None else None)
        concepts.add("recall", float(cr) if cr is not None else None)
        concepts.add("f1", cf)
        topics.add("precision", float(tp) if tp is not None else None)
        topics.add("recall", float(tr) if tr is not None else None)
        topics.add("f1", tf)
    return [concepts, topics]


def build_refs_resolution_aggs(cases: list[dict[str, Any]]) -> list[SlotAgg]:
    slot = SlotAgg(
        "references_resolution_mini",
        "References resolution mini — span to canonical key ( P/R/F1 )",
        "prf1",
    )
    for case in cases:
        m = case.get("metrics") or {}
        pr = m.get("resolution_precision")
        rc = m.get("resolution_recall")
        f1v = _f1_from_pr(
            float(pr) if pr is not None else None, float(rc) if rc is not None else None
        )
        slot.add("precision", float(pr) if pr is not None else None)
        slot.add("recall", float(rc) if rc is not None else None)
        slot.add("f1", f1v)
    return [slot]


def build_claims_aggs(cases: list[dict[str, Any]], split_label: str) -> list[SlotAgg]:
    slot = SlotAgg(
        f"claims_paraphrase_{split_label}",
        f"Claims paraphrase ( {split_label} ) — claim-level P/R/F1",
        "prf1",
    )
    for case in cases:
        m = case.get("metrics") or {}
        pr = m.get("claim_precision")
        rc = m.get("claim_recall")
        f1v = _f1_from_pr(
            float(pr) if pr is not None else None, float(rc) if rc is not None else None
        )
        slot.add("precision", float(pr) if pr is not None else None)
        slot.add("recall", float(rc) if rc is not None else None)
        slot.add("f1", f1v)
    return [slot]


def _graph_expectations_stats(cases: list[dict[str, Any]]) -> dict[str, Any]:
    """How many layer1 golds declare non-empty expected cited arXiv (graph contract hint)."""

    nonempty = 0
    total = 0
    for case in cases:
        gold = case.get("gold")
        if not isinstance(gold, dict):
            continue
        total += 1
        ge = gold.get("graph_expectations")
        if not isinstance(ge, dict):
            continue
        exp = ge.get("expected_cited_arxiv_ids")
        if isinstance(exp, list) and any(str(x).strip() for x in exp):
            nonempty += 1
    return {
        "layer1_cases_with_gold": total,
        "cases_with_nonempty_expected_cited_arxiv": nonempty,
        "note": (
            "Neo4j-level CITES / cited_arxiv F1 is produced by `science-graphrag-graph-benchmark`, "
            "not embedded in layer1 suite JSON."
        ),
    }


def _fmt(x: float | None, nd: int = 3) -> str:
    if x is None:
        return "—"
    return f"{x:.{nd}f}"


def render_markdown(
    payload: dict[str, Any],
    *,
    rows: list[dict[str, Any]],
) -> str:
    lines: list[str] = []
    lines.append("<!-- Generated by scripts/report_extraction_entity_metrics.py -->")
    lines.append("")
    lines.append("### Extraction quality by entity slot (macro mean over benchmark cases)")
    lines.append("")
    rm = payload.get("run_metadata") or {}
    model = rm.get("extraction_llm_model") or "(see per-artifact run_metadata)"
    lines.append(f"**Extraction model (layer1 artifact):** `{model}`")
    lines.append("")
    lines.append(
        "| Slot | Kind | Mean | Notes |",
    )
    lines.append("|------|------|------|-------|")
    for row in rows:
        label = str(row.get("label") or row.get("slot_id"))
        family = str(row.get("metric_family") or "")
        mm = row.get("macro_mean") or {}
        if family == "prf1":
            cell = (
                f"P={_fmt(mm.get('precision'))} R={_fmt(mm.get('recall'))} F1={_fmt(mm.get('f1'))}"
            )
        else:
            cell = f"score={_fmt(mm.get('score'))}"
        n = row.get("n_cases_with_value") or {}
        n_note = ", ".join(f"{k}={v}" for k, v in sorted(n.items()))
        lines.append(f"| {label} | {family} | {cell} | n {n_note} |")
    lines.append("")
    notes = payload.get("notes") or {}
    if isinstance(notes, dict) and notes.get("graph_expectations"):
        ge = notes["graph_expectations"]
        lines.append(
            f"**Graph CITES note:** {ge.get('note', '')} "
            f"(gold cases with non-empty `expected_cited_arxiv_ids`: "
            f"{ge.get('cases_with_nonempty_expected_cited_arxiv')}/"
            f"{ge.get('layer1_cases_with_gold')})."
        )
        lines.append("")
    return "\n".join(lines)


def _resolve_path(repo_root: Path, p: str) -> Path:
    path = Path(p)
    if not path.is_absolute():
        path = (repo_root / path).resolve()
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=ROOT,
        help="Repository root (defaults to science-graphrag root).",
    )
    parser.add_argument("--layer1-json", type=str, default=DEFAULT_LAYER1_NIGHTLY)
    parser.add_argument("--layer2-json", type=str, default=DEFAULT_LAYER2_NIGHTLY)
    parser.add_argument(
        "--claims-pilot-json",
        type=str,
        default=DEFAULT_CLAIMS_PARAPHRASE_PILOT,
        help="Claims paraphrase pilot suite (e.g. claims_pilot_v2).",
    )
    parser.add_argument(
        "--claims-holdout-json",
        type=str,
        default=DEFAULT_CLAIMS_PARAPHRASE_HOLDOUT,
        help="Claims paraphrase holdout suite (e.g. claims_holdout_v1).",
    )
    parser.add_argument(
        "--concept-topic-json",
        type=str,
        default=DEFAULT_CONCEPT_TOPIC_MINI_SUITE,
        help="Concept / research-topic mini suite JSON.",
    )
    parser.add_argument(
        "--references-resolution-json",
        type=str,
        default=DEFAULT_REFERENCES_RESOLUTION_MINI,
        help="References resolution mini suite JSON.",
    )
    parser.add_argument(
        "--out-json",
        type=str,
        default="eval/results/extraction-entity-metrics-for-report.json",
    )
    parser.add_argument(
        "--out-md",
        type=str,
        default="eval/results/extraction-entity-metrics-for-report.md",
    )
    args = parser.parse_args(argv)
    repo_root: Path = args.repo_root.resolve()

    inputs: dict[str, str] = {
        "layer1": args.layer1_json,
        "layer2": args.layer2_json,
        "claims_pilot": args.claims_pilot_json,
        "claims_holdout": args.claims_holdout_json,
        "concept_topic": args.concept_topic_json,
        "references_resolution": args.references_resolution_json,
    }

    all_rows: list[dict[str, Any]] = []
    run_meta_primary: dict[str, Any] = {}

    l1_path = _resolve_path(repo_root, args.layer1_json)
    if l1_path.is_file():
        raw1, c1 = _read_suite_cases(l1_path)
        run_meta_primary = dict(raw1.get("run_metadata") or {})
        for slot in build_layer1_aggs(c1):
            all_rows.append(slot.to_row())
        graph_note = _graph_expectations_stats(c1)
    else:
        graph_note = {"error": f"missing_layer1_file:{l1_path}"}

    l2_path = _resolve_path(repo_root, args.layer2_json)
    if l2_path.is_file():
        raw2, c2 = _read_suite_cases(l2_path)
        if not run_meta_primary:
            run_meta_primary = dict(raw2.get("run_metadata") or {})
        for slot in build_layer2_aggs(c2):
            all_rows.append(slot.to_row())

    cp = _resolve_path(repo_root, args.claims_pilot_json)
    if cp.is_file():
        _, cc = _read_suite_cases(cp)
        for slot in build_claims_aggs(cc, "pilot"):
            all_rows.append(slot.to_row())

    ch = _resolve_path(repo_root, args.claims_holdout_json)
    if ch.is_file():
        _, cc = _read_suite_cases(ch)
        for slot in build_claims_aggs(cc, "holdout"):
            all_rows.append(slot.to_row())

    ct = _resolve_path(repo_root, args.concept_topic_json)
    if ct.is_file():
        raw_ct, cases_ct = _read_suite_cases(ct)
        if not run_meta_primary:
            run_meta_primary = dict(raw_ct.get("run_metadata") or {})
        for slot in build_concept_topic_aggs(cases_ct):
            all_rows.append(slot.to_row())

    rr = _resolve_path(repo_root, args.references_resolution_json)
    if rr.is_file():
        raw_rr, cases_rr = _read_suite_cases(rr)
        if not run_meta_primary:
            run_meta_primary = dict(raw_rr.get("run_metadata") or {})
        for slot in build_refs_resolution_aggs(cases_rr):
            all_rows.append(slot.to_row())

    payload: dict[str, Any] = {
        "inputs": {k: str(_resolve_path(repo_root, v)) for k, v in inputs.items()},
        "run_metadata": run_meta_primary,
        "slots": all_rows,
        "notes": {
            "aggregation": "macro_mean_over_cases_skipping_null_metrics",
            "graph_expectations": graph_note,
        },
    }

    out_json = _resolve_path(repo_root, args.out_json)
    out_md = _resolve_path(repo_root, args.out_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md = render_markdown(payload, rows=all_rows)
    out_md.write_text(md, encoding="utf-8")
    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
