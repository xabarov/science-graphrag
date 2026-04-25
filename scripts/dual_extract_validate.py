#!/usr/bin/env python3
"""Phase 6 — dual-LLM validation pass for Corpus Gold Pack v1.

Runs an independent extractor B per pack, diffs it against the existing gold
(extractor A), and writes a ``consistency_report.json`` next to the pack.

Examples:

    # Dry run on one claims pack (no LLM call, only build prompt + skeleton report).
    .venv/bin/python scripts/dual_extract_validate.py \
        --layer claims_v2 \
        --pack tests/fixtures/benchmarks/claims/corpus_yolov1_v2 \
        --dry-run

    # Real run with deepseek (resolves API key from env or --api-key).
    .venv/bin/python scripts/dual_extract_validate.py \
        --layer claims_v2 \
        --pack tests/fixtures/benchmarks/claims/corpus_yolov1_v2 \
        --model deepseek/deepseek-v3.2

Provenance lives in each report's ``extractor_b`` block (model, base_url, prompt_hash,
usage tokens, latency). Reports are deterministic given the same LLM raw response.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from science_graphrag.config import get_settings
from science_graphrag.embeddings import (
    OpenRouterEmbeddingProvider,
    resolve_openrouter_embedding_settings,
)
from scripts.dual_validate.consistency_report import write_report
from scripts.dual_validate.embedding_scorer import EmbeddingScorer
from scripts.dual_validate.extractors import (
    AgentToolsLiveExtractor,
    ClaimsV2Extractor,
    ConceptTopicV2Extractor,
    ContradictionsV1Extractor,
    DedupAuthorsV1Extractor,
    DedupDatasetsV1Extractor,
    DedupInstitutionsV1Extractor,
    DedupMethodsV1Extractor,
    DedupVenuesV1Extractor,
    ExtractorBase,
    HybridAblationV2Extractor,
    IdeaAssistLiveExtractor,
    MultihopV2Extractor,
    WorkspaceScopedLiveExtractor,
)
from scripts.dual_validate.llm_client import (
    DualValidateLLMClient,
    resolve_llm_settings,
)

_EXTRACTORS: dict[str, type[ExtractorBase]] = {
    "agent_tools_live": AgentToolsLiveExtractor,
    "claims_v2": ClaimsV2Extractor,
    "concept_topic_v2": ConceptTopicV2Extractor,
    "contradictions_v1": ContradictionsV1Extractor,
    "dedup_authors_v1": DedupAuthorsV1Extractor,
    "dedup_institutions_v1": DedupInstitutionsV1Extractor,
    "dedup_venues_v1": DedupVenuesV1Extractor,
    "dedup_methods_v1": DedupMethodsV1Extractor,
    "dedup_datasets_v1": DedupDatasetsV1Extractor,
    "idea_assist_live": IdeaAssistLiveExtractor,
    "workspace_scoped_live": WorkspaceScopedLiveExtractor,
    "hybrid_ablation_v2": HybridAblationV2Extractor,
    "multihop_v2": MultihopV2Extractor,
}


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Dual-LLM validation pass (Phase 6).")
    p.add_argument(
        "--layer",
        choices=sorted(_EXTRACTORS.keys()),
        required=True,
        help="Which Corpus Gold Pack v1 layer to validate.",
    )
    p.add_argument(
        "--fixtures-root",
        type=Path,
        default=ROOT / "tests/fixtures/benchmarks",
        help="Benchmarks fixtures root.",
    )
    p.add_argument(
        "--pack",
        type=Path,
        action="append",
        default=None,
        help="Specific pack directory to validate. May be repeated. Default: all in layer.",
    )
    p.add_argument(
        "--report-name",
        default="consistency_report.json",
        help="Filename written into each pack directory.",
    )
    p.add_argument("--dry-run", action="store_true", help="Build prompt and report skeleton only.")
    p.add_argument("--api-key", type=str, default=None)
    p.add_argument("--base-url", type=str, default=None)
    p.add_argument(
        "--model",
        type=str,
        default=None,
        help=(
            "LLM model id (default: SCIENCE_GRAPHRAG_BENCHMARK_TEACHER_LLM_MODEL "
            "or deepseek/deepseek-v3.2)."
        ),
    )
    p.add_argument(
        "--save-raw-response",
        action="store_true",
        help="Save the LLM raw response next to the consistency report (.raw.json).",
    )
    p.add_argument(
        "--rebuild-from-raw",
        action="store_true",
        help=(
            "Skip the LLM call: re-derive the consistency report from the saved "
            "<report-name>.raw.json. Useful for matcher tuning without spending tokens."
        ),
    )
    p.add_argument(
        "--with-embeddings",
        action="store_true",
        help=(
            "Enable the embedding cascade in the matcher (Phase 6.D). Pairs whose "
            "lexical score is below the accept threshold get re-scored with cosine "
            "similarity over OpenRouter embeddings (cached on disk)."
        ),
    )
    p.add_argument(
        "--embedding-model",
        type=str,
        default=None,
        help=(
            "Embedding model id on OpenRouter (default: $EMBEDDING_MODEL "
            "or 'baai/bge-m3'). Only consulted when --with-embeddings is set."
        ),
    )
    p.add_argument(
        "--embedding-cache-root",
        type=Path,
        default=ROOT / "eval/dual_validate/embeddings_cache",
        help="Directory for per-text embedding cache files (one JSON per text+model).",
    )
    p.add_argument(
        "--promote-validation-status",
        action="store_true",
        help=(
            "After processing, write back meta.validation_status = 'llm_dual_validated' "
            "into each gold.json whose consistency report has spot_check_priority in "
            "{low, medium}. Idempotent."
        ),
    )
    return p.parse_args()


def main() -> int:
    """Iterate selected packs, optionally hit the LLM, write consistency reports."""

    args = _parse_args()
    extractor = _EXTRACTORS[args.layer]()

    if args.pack:
        packs = [p.resolve() for p in args.pack]
    else:
        packs = extractor.discover_packs(args.fixtures_root)
    if not packs:
        print("no packs to validate", file=sys.stderr)
        return 1

    settings = get_settings() if not args.dry_run else None
    if args.dry_run or args.rebuild_from_raw:
        client = None
        model = (args.model or "").strip() or "deepseek/deepseek-v3.2"
        base_url = (args.base_url or "").strip() or "https://openrouter.ai/api/v1"
        if args.rebuild_from_raw:
            print("rebuild-from-raw: skipping LLM, reusing saved raw responses", file=sys.stderr)
    else:
        api_key, base_url, model = resolve_llm_settings(
            settings=settings,
            cli_api_key=args.api_key,
            cli_base_url=args.base_url,
            cli_model=args.model,
        )
        client = DualValidateLLMClient(api_key=api_key, base_url=base_url)
        print(f"using model={model} base_url={base_url}", file=sys.stderr)

    embedding_scorer = None
    if args.with_embeddings:
        if settings is None:
            settings = get_settings()
        emb_cfg = resolve_openrouter_embedding_settings(
            settings=settings,
            cli_api_key=args.api_key,
            cli_base_url=args.base_url,
            cli_model=args.embedding_model,
            cache_root=args.embedding_cache_root,
        )
        embedding_provider = OpenRouterEmbeddingProvider(emb_cfg)
        embedding_scorer = EmbeddingScorer(provider=embedding_provider)
        print(
            f"embeddings enabled: model={emb_cfg.model} "
            f"cache={emb_cfg.cache_root / emb_cfg.model.replace('/', '__')}",
            file=sys.stderr,
        )

    summary_rows: list[dict] = []
    for pack in packs:
        gold_path = pack / "gold.json"
        if not gold_path.exists():
            print(f"  skip {pack.name}: no gold.json", file=sys.stderr)
            continue
        gold_a = json.loads(gold_path.read_text())
        try:
            if args.rebuild_from_raw:
                raw_name = args.report_name.removesuffix(".json") + ".raw.json"
                raw_path = pack / raw_name
                if not raw_path.exists():
                    print(f"  skip {pack.name}: missing {raw_path.name}", file=sys.stderr)
                    continue
                report_path_existing = pack / args.report_name
                prior = (
                    json.loads(report_path_existing.read_text())
                    if report_path_existing.exists()
                    else None
                )
                run = extractor.rebuild_run_from_raw(pack, raw_path=raw_path, prior_report=prior)
            else:
                run, _spec = extractor.run_for_pack(
                    pack, client=client, model=model, base_url=base_url, dry_run=args.dry_run
                )
        except Exception as exc:  # pylint: disable=broad-except
            print(f"  ERROR on {pack.name}: {exc}", file=sys.stderr)
            continue
        report = extractor.build_report(
            pack,
            run=run,
            gold_a=gold_a,
            embedding_scorer=embedding_scorer,
        )
        report_path = pack / args.report_name
        write_report(report, report_path)
        promoted = False
        if args.promote_validation_status and report.spot_check_priority in {"low", "medium"}:
            promoted = _promote_validation_status(
                gold_path,
                report_path=report_path,
                priority=report.spot_check_priority,
            )
        summary_rows.append(
            {
                "pack": pack.name,
                "spot_check_priority": report.spot_check_priority,
                "matched": report.summary["matched"],
                "matched_lexical": report.summary.get("matched_lexical", report.summary["matched"]),
                "matched_embedding": report.summary.get("matched_embedding", 0),
                "unmatched_a": report.summary["unmatched_a"],
                "unmatched_b": report.summary["unmatched_b"],
                "promoted_to_llm_dual_validated": promoted,
            }
        )
        if args.save_raw_response and run is not None:
            raw_name = args.report_name.removesuffix(".json") + ".raw.json"
            (pack / raw_name).write_text(run.raw_response + "\n", encoding="utf-8")
        emb_note = (
            f" (lex={report.summary.get('matched_lexical', 0)}, "
            f"emb={report.summary.get('matched_embedding', 0)})"
            if args.with_embeddings
            else ""
        )
        promo_note = " [promoted]" if promoted else ""
        print(
            f"  wrote {report_path}  "
            f"priority={report.spot_check_priority}  "
            f"matched={report.summary['matched']}/{report.summary['a_total']}{emb_note}  "
            f"extra_b={report.summary['unmatched_b']}{promo_note}",
            file=sys.stderr,
        )

    print(json.dumps({"layer": args.layer, "model": model, "results": summary_rows}, indent=2))
    return 0


def _promote_validation_status(gold_path: Path, *, report_path: Path, priority: str) -> bool:
    """Idempotently promote ``meta.validation_status`` to ``llm_dual_validated``.

    Returns True when the file was actually changed. Records the consistency report
    path and the priority so reviewers can re-trace the decision.
    """

    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    meta = gold.setdefault("meta", {})
    if meta.get("validation_status") == "llm_dual_validated":
        return False
    meta["validation_status"] = "llm_dual_validated"
    history = meta.setdefault("validation_history", [])
    history.append(
        {
            "promoted_at_utc": json_iso_utcnow(),
            "from_status": meta.get("validation_status_previous", "draft"),
            "to_status": "llm_dual_validated",
            "spot_check_priority": priority,
            "consistency_report": _safe_relative(report_path),
            "rule": "auto-promote on Phase 6.D embedding-cascade pass",
        }
    )
    meta["validation_status_previous"] = "draft"
    meta["needs_human_review"] = priority == "medium"
    gold_path.write_text(
        json.dumps(gold, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return True


def json_iso_utcnow() -> str:
    """ISO-8601 UTC timestamp; broken out for deterministic mocking in tests."""

    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _safe_relative(path: Path) -> str:
    """Best-effort relative path against CWD; falls back to absolute string outside it."""

    try:
        return str(path.resolve().relative_to(Path.cwd()))
    except ValueError:
        return str(path.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
