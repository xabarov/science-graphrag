#!/usr/bin/env python3
"""Phase 6.E — triple-vote consensus across N independent extractor-B passes.

Reads per-model consistency reports written by ``dual_extract_validate.py`` and
produces a layer-agnostic consensus per pack:

* **Priority majority vote** — each model independently classifies the pack
  (``low|medium|high``) via its layer-specific ``_classify_priority`` rule.
  The consensus uses majority; ties resolve to the more conservative bucket.
* **Per-record vote** (when a stable ``a_id`` exists in ``matched_pairs``):
  for every gold-A record, count how many models matched it. ``matched_by_all``
  / ``matched_by_majority`` / ``controversial`` / ``missed_by_all`` buckets
  feed the rationale.

Outputs:

* ``consensus_report.json`` next to each pack (schema v1).
* Optionally promotes ``meta.validation_status`` to ``llm_triple_validated``
  when consensus_priority ∈ {low, medium}, recording history.
* JSON layer summary on stdout (and optional ``--summary-output``).

Conventions:

* Single-model reports written before Phase 6.E live at ``consistency_report.json``;
  we treat them as ``deepseek`` by default (override with ``--legacy-tag``).
* Per-model reports follow ``consistency_report.<tag>.json``.

Examples::

    .venv/bin/python scripts/dual_validate/triple_vote_consensus.py \
        --layer claims_v2 \
        --tags deepseek kimi claude \
        --write-consensus --promote
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CONSENSUS_REPORT_SCHEMA_VERSION = 1


# ---------------------------------------------------------------------------
# Layer-specific record-id conventions
# ---------------------------------------------------------------------------

# Maps consistency_report.layer -> key inside each matched_pair that uniquely
# identifies the gold-A record. ``None`` disables per-record voting (the layer
# stores no stable id, e.g. multihop_v2 reports have empty matched_pairs).
LAYER_RECORD_KEYS: dict[str, str | None] = {
    "claims_v2": "a_claim_id",
    "concept_topic_v2": "concept_id",
    "contradictions_v1": "pair_id",
    "dedup_authors_v1": "a_cluster_id",
    "dedup_institutions_v1": "a_cluster_id",
    "dedup_venues_v1": "a_cluster_id",
    "dedup_methods_v1": "a_cluster_id",
    "dedup_datasets_v1": "a_cluster_id",
    "hybrid_ablation_v2": "corpus_work_id",
    "idea_assist_live": "claim_id",
    "workspace_scoped_live": "corpus_work_id",
    # Layers without per-record voting:
    "agent_tools_live": None,  # tool_name ids vary per model
    "multihop_v2": None,  # matched_pairs intentionally empty
}


PRIORITY_RANK = {"low": 0, "medium": 1, "high": 2}


@dataclass(frozen=True)
class ModelReport:
    tag: str
    path: Path
    priority: str
    matched_pair_ids: tuple[str, ...]
    summary: dict[str, Any]


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def _report_filename(tag: str, *, legacy_tag: str) -> str:
    """``deepseek`` keeps the legacy unsuffixed name; everything else gets ``.<tag>.json``."""

    return "consistency_report.json" if tag == legacy_tag else f"consistency_report.{tag}.json"


def _load_model_report(
    pack_dir: Path,
    *,
    tag: str,
    legacy_tag: str,
    record_key: str | None,
) -> ModelReport | None:
    path = pack_dir / _report_filename(tag, legacy_tag=legacy_tag)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    matched_ids: list[str] = []
    if record_key is not None:
        for pair in data.get("matched_pairs", []) or []:
            value = pair.get(record_key)
            if value is not None:
                matched_ids.append(str(value))
    return ModelReport(
        tag=tag,
        path=path,
        priority=str(data.get("spot_check_priority", "high")),
        matched_pair_ids=tuple(matched_ids),
        summary=dict(data.get("summary", {})),
    )


# ---------------------------------------------------------------------------
# Voting
# ---------------------------------------------------------------------------


def _priority_majority(priorities: list[str]) -> tuple[str, str]:
    """Majority vote with conservative tie-break (favour the higher rank)."""

    counts = Counter(priorities)
    top_count = max(counts.values())
    winners = sorted(
        (p for p, c in counts.items() if c == top_count),
        key=lambda p: PRIORITY_RANK.get(p, 99),
        reverse=True,
    )
    winner = winners[0]
    rationale = (
        f"votes={dict(counts)}; tie_break={'conservative' if len(winners) > 1 else 'majority'}"
    )
    return winner, rationale


def _per_record_consensus(
    reports: list[ModelReport],
    *,
    record_key: str | None,
) -> dict[str, Any] | None:
    """Cross-model record vote; ``None`` for layers without stable ids."""

    if record_key is None:
        return None
    all_ids = sorted({rid for r in reports for rid in r.matched_pair_ids})
    # Also consider records that no model matched: pull from extractor_a counts when available.
    # Conservative fallback: use the union of matched ids only — missed-by-all is invisible here
    # but the ``unmatched_a`` block of any report tells the same story.
    records = []
    bucket_counts: Counter[str] = Counter()
    for rid in all_ids:
        matched_by = [r.tag for r in reports if rid in r.matched_pair_ids]
        missing_in = [r.tag for r in reports if rid not in r.matched_pair_ids]
        if len(matched_by) == len(reports):
            bucket = "matched_by_all"
        elif len(matched_by) > len(reports) // 2:
            bucket = "matched_by_majority"
        else:
            bucket = "controversial"
        bucket_counts[bucket] += 1
        records.append(
            {
                "id": rid,
                "matched_by": matched_by,
                "missing_in": missing_in,
                "consensus": bucket,
            }
        )
    a_total = max((r.summary.get("a_total", 0) for r in reports), default=0)
    matched_total = bucket_counts.get("matched_by_all", 0) + bucket_counts.get(
        "matched_by_majority", 0
    )
    return {
        "id_field": record_key,
        "a_total_records": a_total,
        "consensus_matched_count": matched_total,
        "consensus_match_ratio": round(matched_total / a_total, 3) if a_total else 0.0,
        "buckets": dict(bucket_counts),
        "records": records,
    }


# ---------------------------------------------------------------------------
# Per-pack consensus
# ---------------------------------------------------------------------------


def build_consensus(
    pack_dir: Path,
    *,
    layer: str,
    tags: list[str],
    legacy_tag: str,
) -> tuple[dict[str, Any], list[ModelReport], list[str]]:
    """Returns (consensus_dict, loaded_reports, missing_tags)."""

    record_key = LAYER_RECORD_KEYS.get(layer)
    loaded: list[ModelReport] = []
    missing: list[str] = []
    for tag in tags:
        rep = _load_model_report(pack_dir, tag=tag, legacy_tag=legacy_tag, record_key=record_key)
        if rep is None:
            missing.append(tag)
        else:
            loaded.append(rep)

    if not loaded:
        raise RuntimeError(f"no per-model reports found in {pack_dir}")

    priorities = [r.priority for r in loaded]
    consensus_priority, rationale = _priority_majority(priorities)
    per_record = _per_record_consensus(loaded, record_key=record_key)

    consensus = {
        "schema_version": CONSENSUS_REPORT_SCHEMA_VERSION,
        "pack_id": f"{pack_dir.parent.name}/{pack_dir.name}",
        "pack_path": _safe_relative(pack_dir),
        "layer": layer,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "tags_requested": tags,
        "tags_present": [r.tag for r in loaded],
        "tags_missing": missing,
        "consensus_priority": consensus_priority,
        "consensus_priority_rationale": rationale,
        "votes_by_priority": dict(Counter(priorities)),
        "model_reports": [
            {
                "tag": r.tag,
                "report_path": _safe_relative(r.path),
                "priority": r.priority,
                "summary": r.summary,
                "matched_pair_count": len(r.matched_pair_ids),
            }
            for r in loaded
        ],
        "per_record_consensus": per_record,
    }
    return consensus, loaded, missing


# ---------------------------------------------------------------------------
# Promotion
# ---------------------------------------------------------------------------


def _promote_status(
    gold_path: Path,
    *,
    consensus_priority: str,
    consensus_path: Path,
    n_models_present: int,
) -> bool:
    """Idempotently set ``meta.validation_status`` to ``llm_triple_validated``."""

    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    meta = gold.setdefault("meta", {})
    if meta.get("validation_status") == "llm_triple_validated":
        return False
    previous = meta.get("validation_status", "draft")
    meta["validation_status"] = "llm_triple_validated"
    history = meta.setdefault("validation_history", [])
    history.append(
        {
            "promoted_at_utc": datetime.now(timezone.utc).isoformat(),
            "from_status": previous,
            "to_status": "llm_triple_validated",
            "consensus_priority": consensus_priority,
            "n_models_present": n_models_present,
            "consensus_report": _safe_relative(consensus_path),
            "rule": "auto-promote on Phase 6.E triple-vote consensus (≥2 of N models)",
        }
    )
    meta["validation_status_previous"] = previous
    meta["needs_human_review"] = consensus_priority == "medium"
    gold_path.write_text(
        json.dumps(gold, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _safe_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd()))
    except ValueError:
        return str(path.resolve())


def _discover_packs(fixtures_root: Path, layer: str) -> list[Path]:
    """Tiny re-implementation; per-extractor discovery is encapsulated in
    each extractor class but here we rely on filesystem layout (faster & avoids
    instantiating heavy extractors just to list packs)."""

    layer_paths = {
        "claims_v2": fixtures_root / "claims",
        "concept_topic_v2": fixtures_root / "concept_topic",
        "contradictions_v1": fixtures_root / "contradictions_v1",
        "dedup_authors_v1": fixtures_root / "dedup",
        "dedup_institutions_v1": fixtures_root / "dedup",
        "dedup_venues_v1": fixtures_root / "dedup",
        "dedup_methods_v1": fixtures_root / "dedup",
        "dedup_datasets_v1": fixtures_root / "dedup",
        "idea_assist_live": fixtures_root / "idea_assist_v1",
        "workspace_scoped_live": fixtures_root / "retrieval/workspace_scoped_live",
        "hybrid_ablation_v2": fixtures_root / "retrieval/hybrid_ablation_v2",
        "multihop_v2": fixtures_root / "retrieval/multihop_v2",
        "agent_tools_live": fixtures_root / "agent_tools_v1",
    }
    base = layer_paths.get(layer)
    if base is None or not base.exists():
        return []
    # dedup keeps a single pack per entity in <type>s_v1/
    if layer.startswith("dedup_"):
        entity = layer[len("dedup_") : -len("_v1")]
        single = base / f"{entity}s_v1"
        return [single] if (single / "gold.json").exists() else []
    packs = sorted(d for d in base.iterdir() if d.is_dir() and (d / "gold.json").exists())
    if layer == "agent_tools_live":
        packs = [p for p in packs if p.name.startswith("live_")]
    return packs


def main() -> int:
    p = argparse.ArgumentParser(description="Phase 6.E triple-vote consensus aggregator.")
    p.add_argument("--layer", required=True, choices=sorted(LAYER_RECORD_KEYS.keys()))
    p.add_argument(
        "--tags",
        nargs="+",
        default=["deepseek", "kimi", "claude"],
        help="Model tags to vote with. ``deepseek`` reads the legacy "
        "consistency_report.json; everything else reads consistency_report.<tag>.json.",
    )
    p.add_argument(
        "--legacy-tag",
        default="deepseek",
        help="Tag whose report uses the legacy unsuffixed filename.",
    )
    p.add_argument("--fixtures-root", type=Path, default=ROOT / "tests/fixtures/benchmarks")
    p.add_argument("--pack", type=Path, action="append", default=None)
    p.add_argument(
        "--write-consensus",
        action="store_true",
        help="Write consensus_report.json next to each pack.",
    )
    p.add_argument(
        "--promote",
        action="store_true",
        help="Promote gold.json validation_status to llm_triple_validated when consensus is "
        "low or medium and ≥2 models are present.",
    )
    p.add_argument("--summary-output", type=Path, default=None)
    p.add_argument(
        "--require-min-models",
        type=int,
        default=2,
        help="Skip packs where fewer than this many model reports are present (default: 2).",
    )
    args = p.parse_args()

    packs = (
        [path.resolve() for path in args.pack]
        if args.pack
        else _discover_packs(args.fixtures_root, args.layer)
    )
    if not packs:
        print(f"no packs discovered for layer={args.layer}", file=sys.stderr)
        return 1

    rows: list[dict[str, Any]] = []
    for pack in packs:
        try:
            consensus, loaded, missing = build_consensus(
                pack, layer=args.layer, tags=args.tags, legacy_tag=args.legacy_tag
            )
        except RuntimeError as exc:
            print(f"  skip {pack.name}: {exc}", file=sys.stderr)
            continue
        n_present = len(loaded)
        if n_present < args.require_min_models:
            print(
                f"  skip {pack.name}: only {n_present} model reports " f"(missing: {missing})",
                file=sys.stderr,
            )
            continue

        consensus_path = pack / "consensus_report.json"
        if args.write_consensus:
            consensus_path.write_text(
                json.dumps(consensus, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

        promoted = False
        if args.promote and consensus["consensus_priority"] in {"low", "medium"}:
            gold_path = pack / "gold.json"
            promoted = _promote_status(
                gold_path,
                consensus_priority=consensus["consensus_priority"],
                consensus_path=consensus_path,
                n_models_present=n_present,
            )

        rows.append(
            {
                "pack": pack.name,
                "n_models_present": n_present,
                "tags_missing": missing,
                "consensus_priority": consensus["consensus_priority"],
                "votes_by_priority": consensus["votes_by_priority"],
                "per_record_match_ratio": (
                    consensus["per_record_consensus"]["consensus_match_ratio"]
                    if consensus["per_record_consensus"]
                    else None
                ),
                "promoted": promoted,
            }
        )
        record_match = (
            f"  records={consensus['per_record_consensus']['consensus_match_ratio']}"
            if consensus["per_record_consensus"]
            else ""
        )
        promo_note = " [promoted]" if promoted else ""
        print(
            f"  {pack.name:55s}  consensus={consensus['consensus_priority']:6s}"
            f"  votes={consensus['votes_by_priority']}{record_match}{promo_note}",
            file=sys.stderr,
        )

    summary = {
        "layer": args.layer,
        "tags": args.tags,
        "totals": {
            "packs_seen": len(packs),
            "packs_with_consensus": len(rows),
            "consensus_low": sum(1 for r in rows if r["consensus_priority"] == "low"),
            "consensus_medium": sum(1 for r in rows if r["consensus_priority"] == "medium"),
            "consensus_high": sum(1 for r in rows if r["consensus_priority"] == "high"),
            "promoted": sum(1 for r in rows if r["promoted"]),
        },
        "results": rows,
    }
    text = json.dumps(summary, indent=2, ensure_ascii=False)
    print(text)
    if args.summary_output is not None:
        args.summary_output.parent.mkdir(parents=True, exist_ok=True)
        args.summary_output.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
