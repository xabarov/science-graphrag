"""LLM-judge advisory for retrieval answers (Wave P)."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from time import perf_counter
from typing import Any

import typer
from pydantic import BaseModel, Field

from eval.bench_common import benchmark_run_metadata
from science_graphrag.config import Settings, get_settings
from science_graphrag.ingestion.llm.extractor import SyncInstructorExtractor

JUDGE_PROMPT_PATH = Path(__file__).with_name("judge_prompt_v1.md")
JUDGE_SCHEMA_VERSION = "retrieval_judge_v1"


class RetrievalJudgeScores(BaseModel):
    factuality: int = Field(ge=0, le=3)
    coverage: int = Field(ge=0, le=3)
    no_contradictions: int = Field(ge=0, le=2)
    language: int = Field(ge=0, le=2)
    justification: str = Field(default="", max_length=2000)


def judge_prompt_fingerprint() -> str:
    raw = JUDGE_PROMPT_PATH.read_bytes()
    h = hashlib.sha256(raw).hexdigest()[:20]
    return f"sha256-20:{h}"


def weighted_judge_score(row: RetrievalJudgeScores) -> float:
    return (
        1.0 * float(row.factuality)
        + 0.7 * float(row.coverage)
        + 0.5 * float(row.no_contradictions)
        + 0.3 * float(row.language)
    )


def _judge_system_prompt() -> str:
    return JUDGE_PROMPT_PATH.read_text(encoding="utf-8")


def _judge_llm_settings(settings: Settings) -> tuple[str, str, str | None]:
    """Optional env overrides for anti-overfit (BT5): ``RETRIEVAL_JUDGE_LLM_*``."""

    model = os.environ.get("RETRIEVAL_JUDGE_LLM_MODEL", "").strip() or settings.extraction_llm_model
    base = (
        os.environ.get("RETRIEVAL_JUDGE_LLM_BASE_URL", "").strip().rstrip("/")
        or settings.extraction_llm_base_url
    )
    api_key = (
        os.environ.get("RETRIEVAL_JUDGE_LLM_API_KEY", "").strip() or settings.extraction_llm_api_key
    )
    return model, base, api_key


def judge_retrieval_case(
    *,
    question: str,
    answer: str,
    gold_reference: str,
    citation_excerpts: list[str],
    settings: Settings,
) -> tuple[RetrievalJudgeScores | None, str | None]:
    excerpts_block = "\n".join(f"- {x[:500]}" for x in citation_excerpts[:12] if x.strip())
    user = (
        f"Question:\n{question}\n\n"
        f"Answer:\n{answer}\n\n"
        f"Gold reference snippet:\n{gold_reference or '(none)'}\n\n"
        f"Citation excerpts:\n{excerpts_block or '(none)'}\n"
    )
    j_model, j_base, j_key = _judge_llm_settings(settings)
    ext = SyncInstructorExtractor(
        api_key=j_key,
        base_url=j_base,
        model=j_model,
        temperature=0.0,
        max_tokens=1024,
        timeout_seconds=min(float(settings.extraction_llm_timeout_seconds), 120.0),
        mode=settings.extraction_llm_mode,
    )
    parsed, err = ext.extract_maybe(RetrievalJudgeScores, system=_judge_system_prompt(), user=user)
    if err or parsed is None:
        return None, str(err) if err else "empty_parse"
    return parsed, None


def _case_ids_for_tier(fixtures_root: Path, tier_key: str) -> set[str]:
    p = fixtures_root / "case_tiers.json"
    if not p.is_file():
        return set()
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return set()
    ids = raw.get(tier_key)
    if not isinstance(ids, list):
        return set()
    return {str(x) for x in ids if str(x)}


def run_judge_on_retrieval_json(
    retrieval_path: Path,
    *,
    fixtures_root: Path,
    settings: Settings,
    min_weighted_score: float = 4.5,
    case_ids_allowlist: set[str] | None = None,
) -> dict[str, Any]:
    data = json.loads(retrieval_path.read_text(encoding="utf-8"))
    cases_in = data.get("cases") or []
    reports: list[dict[str, Any]] = []
    for row in cases_in:
        cid = str(row.get("case_id") or "")
        if case_ids_allowlist is not None and cid not in case_ids_allowlist:
            continue
        case_dir = fixtures_root / cid
        gold_path = case_dir / "gold.json"
        gold: dict[str, Any] = {}
        if gold_path.is_file():
            gold = json.loads(gold_path.read_text(encoding="utf-8"))
        ref = str(gold.get("answer_reference_text") or "").strip()
        question = str(row.get("question") or row.get("question_preview") or "").strip()
        answer = str(row.get("answer") or row.get("answer_preview") or "").strip()
        excerpts: list[str] = []
        for c in row.get("citations") or []:
            if isinstance(c, dict) and c.get("excerpt"):
                excerpts.append(str(c["excerpt"]))
        started = perf_counter()
        scores, err = judge_retrieval_case(
            question=question,
            answer=answer,
            gold_reference=ref,
            citation_excerpts=excerpts,
            settings=settings,
        )
        elapsed = perf_counter() - started
        if scores is None:
            reports.append(
                {
                    "case_id": cid,
                    "passed": False,
                    "weighted_score": None,
                    "error": err,
                    "wall_clock_seconds": round(elapsed, 3),
                },
            )
            continue
        w = weighted_judge_score(scores)
        reports.append(
            {
                "case_id": cid,
                "passed": bool(w + 1e-9 >= min_weighted_score),
                "weighted_score": round(w, 4),
                "scores": scores.model_dump(),
                "wall_clock_seconds": round(elapsed, 3),
            },
        )

    weighted_vals = [
        float(r["weighted_score"]) for r in reports if r.get("weighted_score") is not None
    ]
    mean_w = sum(weighted_vals) / len(weighted_vals) if weighted_vals else None
    j_model, _, _ = _judge_llm_settings(settings)
    judge_warnings: list[str] = []
    if j_model == settings.extraction_llm_model:
        judge_warnings.append(
            "judge_uses_same_model_as_extraction_set_RETRIEVAL_JUDGE_LLM_MODEL_to_diversify",
        )
    per_case_score_breakdown: list[dict[str, Any]] = []
    for r in reports:
        sc = r.get("scores")
        if isinstance(sc, dict):
            per_case_score_breakdown.append(
                {
                    "case_id": r.get("case_id"),
                    "factuality": sc.get("factuality"),
                    "coverage": sc.get("coverage"),
                    "no_contradictions": sc.get("no_contradictions"),
                    "language": sc.get("language"),
                    "weighted_score": r.get("weighted_score"),
                    "passed": r.get("passed"),
                },
            )
    return {
        "run_metadata": {
            **benchmark_run_metadata(settings),
            "judge_prompt_fingerprint": judge_prompt_fingerprint(),
            "judge_schema_version": JUDGE_SCHEMA_VERSION,
            "retrieval_artifact": str(retrieval_path),
            "judge_llm_model": j_model,
            "judge_consistency_warnings": judge_warnings,
        },
        "summary": {
            "case_count": len(reports),
            "mean_weighted_score": mean_w,
            "all_passed": all(bool(r.get("passed")) for r in reports) if reports else True,
            "retrieval_judge_eval": True,
            "per_case_score_breakdown": per_case_score_breakdown,
        },
        "cases": reports,
    }


def _cli(
    retrieval_json: Path = typer.Argument(
        ...,
        exists=True,
        readable=True,
        help="Suite JSON from science-graphrag-retrieval-benchmark (with full answer field).",
    ),
    fixtures_root: Path | None = typer.Option(
        None,
        "--fixtures-root",
        help=(
            "Directory containing per-case subdirs with gold.json "
            "(default: <repo>/tests/fixtures/benchmarks/retrieval)."
        ),
    ),
    json_out: Path | None = typer.Option(
        None,
        "--json-out",
        help="Write judge report JSON (advisory; command exits 0 even if some cases fail).",
    ),
    min_weighted: float = typer.Option(
        4.5,
        "--min-weighted",
        help="Per-case pass threshold on weighted rubric score (default 4.5 of max 6).",
    ),
    case_tier: str | None = typer.Option(
        None,
        "--case-tier",
        help="Only judge ``case_id`` values listed under this tier in fixtures-root/case_tiers.json "
        "(e.g. judge_holdout_v1 for BT5 holdout).",
    ),
) -> None:
    settings = get_settings()
    fx = fixtures_root
    if fx is None:
        fx = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "benchmarks" / "retrieval"
    if not fx.is_dir():
        typer.echo(f"fixtures root not found: {fx}", err=True)
        raise typer.Exit(code=1)
    allowlist: set[str] | None = None
    if case_tier:
        allowlist = _case_ids_for_tier(fx, case_tier)
        if not allowlist:
            typer.echo(
                f"Unknown or empty case tier {case_tier!r} under {fx / 'case_tiers.json'}", err=True
            )
            raise typer.Exit(code=1)
    payload = run_judge_on_retrieval_json(
        retrieval_json,
        fixtures_root=fx,
        settings=settings,
        min_weighted_score=min_weighted,
        case_ids_allowlist=allowlist,
    )
    txt = json.dumps(payload, indent=2, ensure_ascii=False)
    typer.echo(txt)
    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(txt + "\n", encoding="utf-8")
        typer.echo(f"Wrote {json_out}", err=True)


def main() -> None:
    typer.run(_cli)


if __name__ == "__main__":
    main()
