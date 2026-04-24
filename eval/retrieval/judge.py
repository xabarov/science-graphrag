"""LLM-judge advisory for retrieval answers (Wave P)."""

from __future__ import annotations

import hashlib
import json
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
    ext = SyncInstructorExtractor(
        api_key=settings.extraction_llm_api_key,
        base_url=settings.extraction_llm_base_url,
        model=settings.extraction_llm_model,
        temperature=0.0,
        max_tokens=1024,
        timeout_seconds=min(float(settings.extraction_llm_timeout_seconds), 120.0),
        mode=settings.extraction_llm_mode,
    )
    parsed, err = ext.extract_maybe(RetrievalJudgeScores, system=_judge_system_prompt(), user=user)
    if err or parsed is None:
        return None, str(err) if err else "empty_parse"
    return parsed, None


def run_judge_on_retrieval_json(
    retrieval_path: Path,
    *,
    fixtures_root: Path,
    settings: Settings,
    min_weighted_score: float = 4.5,
) -> dict[str, Any]:
    data = json.loads(retrieval_path.read_text(encoding="utf-8"))
    cases_in = data.get("cases") or []
    reports: list[dict[str, Any]] = []
    for row in cases_in:
        cid = str(row.get("case_id") or "")
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

    weighted_vals = [float(r["weighted_score"]) for r in reports if r.get("weighted_score") is not None]
    mean_w = sum(weighted_vals) / len(weighted_vals) if weighted_vals else None
    return {
        "run_metadata": {
            **benchmark_run_metadata(settings),
            "judge_prompt_fingerprint": judge_prompt_fingerprint(),
            "judge_schema_version": JUDGE_SCHEMA_VERSION,
            "retrieval_artifact": str(retrieval_path),
        },
        "summary": {
            "case_count": len(reports),
            "mean_weighted_score": mean_w,
            "all_passed": all(bool(r.get("passed")) for r in reports) if reports else True,
            "retrieval_judge_eval": True,
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
) -> None:
    settings = get_settings()
    fx = fixtures_root
    if fx is None:
        fx = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "benchmarks" / "retrieval"
    if not fx.is_dir():
        typer.echo(f"fixtures root not found: {fx}", err=True)
        raise typer.Exit(code=1)
    payload = run_judge_on_retrieval_json(
        retrieval_json,
        fixtures_root=fx,
        settings=settings,
        min_weighted_score=min_weighted,
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
