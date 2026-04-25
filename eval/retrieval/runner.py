"""CLI + library runner for retrieval benchmark cases (Wave F)."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from time import perf_counter
from typing import Any

import typer

from eval.bench_common import run_single_case_json_outputs, run_suite_cli_flow
from eval.retrieval.metrics import score_retrieval_answer
from science_graphrag.config import Settings, get_settings
from science_graphrag.retrieval import GroundedAnswer, answer_query


def _optional_workspace_str(value: Any) -> str | None:
    if value in ("", "null", None):
        return None
    return str(value).strip() or None


def _gold_retrieval_params(gold: dict[str, Any]) -> tuple[str | None, str | None, int, str]:
    work_id = _optional_workspace_str(gold.get("work_id"))
    workspace_id = _optional_workspace_str(gold.get("workspace_id"))
    top_k = gold.get("top_k")
    top_k_i = int(top_k) if top_k is not None else 5
    mode_raw = gold.get("retrieval_mode") or gold.get("mode") or "vector"
    mode_s = "hybrid" if str(mode_raw).strip().lower() == "hybrid" else "vector"
    return work_id, workspace_id, top_k_i, mode_s


def _retrieval_case_report_payload(
    root: Path,
    question: str,
    ga: GroundedAnswer,
    metrics: dict[str, Any],
    elapsed: float,
) -> dict[str, Any]:
    return {
        "case_id": root.name,
        "question": question,
        "question_preview": question[:240],
        "metrics": metrics,
        "retrieval_trace": ga.retrieval_trace,
        "graph_context": ga.graph_context,
        "citations": ga.citations,
        "answer": ga.answer,
        "answer_preview": (ga.answer or "")[:400],
        "wall_clock_seconds": round(elapsed, 3),
    }


def _canned_answer_fn(case_path: Path) -> Callable[..., GroundedAnswer]:
    """Return ``answer_query``-compatible callable that satisfies local ``gold.json`` checks."""

    gold = json.loads((case_path / "gold.json").read_text(encoding="utf-8"))
    contract = bool(gold.get("contract_only"))
    fps = [fp for fp in (gold.get("required_chunk_fingerprints") or []) if fp]

    def inner(
        _question: str,
        *,
        _settings,
        work_id=None,
        _workspace_id=None,
        _top_k=5,
        mode: str = "vector",
    ) -> GroundedAnswer:  # noqa: ARG001
        citations = [
            {"chunk_fingerprint": fp, "rank": i + 1, "excerpt": "stub"} for i, fp in enumerate(fps)
        ]
        min_hits = int(gold.get("min_hit_count") or 0)
        hit_count = 0 if contract else max(min_hits, 1)
        ws_g = str(gold.get("workspace_id") or "").strip()
        members = [str(x) for x in (gold.get("workspace_member_work_ids") or []) if x]
        wid_cit = str(members[0]) if members else None
        if wid_cit:
            for c in citations:
                if isinstance(c, dict):
                    c["work_id"] = wid_cit
        rt: dict[str, Any] = {
            "hit_count": hit_count,
            "embedding": {"embedding_model": "mock"},
            "filter_work_id": work_id,
            "retrieval_mode": str(mode or "vector"),
        }
        if ws_g:
            rt["workspace_id"] = ws_g
            rt["workspace_scope_work_count"] = len(members)
        return GroundedAnswer(
            answer="mock",
            citations=citations,
            graph_context={"semantic_available": False, "methods": [], "datasets": []},
            retrieval_trace=rt,
        )

    return inner


def _load_retrieval_case_tiers(fixtures_root: Path) -> dict[str, list[str]] | None:
    """Parse ``case_tiers.json`` under the retrieval fixtures root (optional)."""

    path = fixtures_root / "case_tiers.json"
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return None
    if not isinstance(raw, dict):
        return None
    out: dict[str, list[str]] = {}
    for key, val in raw.items():
        if isinstance(val, list):
            out[str(key)] = [str(x) for x in val]
    return out or None


def discover_retrieval_case_dirs(
    fixtures_root: Path,
    *,
    tier: str = "merge_safe_contract",
) -> list[Path]:
    """Subdirectories containing ``question.txt`` and ``gold.json``.

    Suite selection:
    - ``tier="all"``: every case except ``skip_in_suite_cli``.
    - ``tier="merge_safe_contract"`` / ``strict_pilot``: if ``case_tiers.json`` exists,
      only case ids listed for that tier; otherwise merge-safe excludes
      ``benchmark_suite_tier=="strict_pilot"`` and behaves like ``all`` for the rest.
    """

    if not fixtures_root.is_dir():
        return []
    tiers = _load_retrieval_case_tiers(fixtures_root)
    has_tiers = tiers is not None
    tiers_dict: dict[str, list[str]] = tiers or {}
    allowed: set[str] | None
    if tier == "all":
        allowed = None
    elif tier in tiers_dict:
        allowed = set(tiers_dict[tier])
    elif has_tiers:
        return []
    else:
        allowed = None

    out: list[Path] = []
    for child in sorted(fixtures_root.iterdir()):
        if not child.is_dir():
            continue
        gold_path = child / "gold.json"
        if not (child / "question.txt").is_file() or not gold_path.is_file():
            continue
        try:
            meta = json.loads(gold_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            meta = {}
        if meta.get("skip_in_suite_cli"):
            continue
        cid = child.name
        if allowed is not None and cid not in allowed:
            continue
        if (
            tier == "merge_safe_contract"
            and allowed is None
            and str(meta.get("benchmark_suite_tier") or "") == "strict_pilot"
        ):
            continue
        out.append(child)
    return out


def _read_retrieval_fixture(root: Path) -> tuple[str, dict[str, Any]]:
    question = (root / "question.txt").read_text(encoding="utf-8").strip()
    gold = json.loads((root / "gold.json").read_text(encoding="utf-8"))
    return question, gold


def run_retrieval_case(
    case_dir: Path | str,
    *,
    settings: Settings | None = None,
    answer_fn: Callable[..., GroundedAnswer] | None = None,
) -> dict[str, Any]:
    """Run ``answer_query`` (or injectable ``answer_fn``) for one fixture directory."""
    root = Path(case_dir)
    question, gold = _read_retrieval_fixture(root)
    s = settings or get_settings()
    fn = answer_fn or answer_query
    work_id, workspace_id, top_k_i, mode_s = _gold_retrieval_params(gold)

    started = perf_counter()
    ga = fn(
        question,
        settings=s,
        work_id=work_id,
        workspace_id=workspace_id,
        top_k=top_k_i,
        mode=mode_s,
    )
    elapsed = perf_counter() - started
    metrics = score_retrieval_answer(ga, gold)
    return _retrieval_case_report_payload(root, question, ga, metrics, elapsed)


def _retrieval_suite_summary(reports: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "all_passed": all(bool((r.get("metrics") or {}).get("passed")) for r in reports),
        "retrieval_eval": True,
    }


def _summarize(report: dict[str, Any]) -> str:
    cid = report.get("case_id")
    passed = bool((report.get("metrics") or {}).get("passed"))
    status = "PASS" if passed else "FAIL"
    return f"## {cid} — {status}\n\n```json\n{json.dumps(report.get('metrics'), indent=2)}\n```\n"


def _cli(
    path: Path = typer.Argument(
        ...,
        exists=True,
        readable=True,
        help="Case directory or suite root containing case subdirectories",
    ),
    suite: bool = typer.Option(False, "--suite", help="Run all cases under PATH"),
    tier: str = typer.Option(
        "merge_safe_contract",
        "--tier",
        help=(
            "Suite tier from case_tiers.json: merge_safe_contract, strict_pilot, "
            "live_corpus_mini (live Qdrant/Neo4j), workspace_scoped (Wave P subdir), or 'all'."
        ),
    ),
    mock_answer: bool = typer.Option(
        False,
        "--mock-answer",
        help=(
            "Do not call Qdrant/Neo4j; canned answers from each case gold.json "
            "(CI / tooling smoke)."
        ),
    ),
    json_out: Path | None = typer.Option(None, "--json-out", help="Write JSON report path"),
    md_out: Path | None = typer.Option(None, "--md-out", help="Write Markdown summary path"),
) -> None:
    _run_retrieval_cli(
        path=path,
        suite=suite,
        tier=tier,
        mock_answer=mock_answer,
        json_out=json_out,
        md_out=md_out,
    )


def _run_retrieval_cli(
    *,
    path: Path,
    suite: bool,
    tier: str,
    mock_answer: bool,
    json_out: Path | None,
    md_out: Path | None,
) -> None:
    settings = get_settings()

    def _is_passed(report: dict[str, Any]) -> bool:
        return bool((report.get("metrics") or {}).get("passed"))

    def _run_one(c: Path) -> dict[str, Any]:
        fn = _canned_answer_fn(c) if mock_answer else None
        return run_retrieval_case(c, settings=settings, answer_fn=fn)

    if suite:
        tiers_map = _load_retrieval_case_tiers(path)
        tiers_map_dict: dict[str, list[str]] = tiers_map or {}
        if tier not in ("all",) and tiers_map is not None and tier not in tiers_map_dict:
            typer.echo(
                f"Unknown --tier {tier!r}; defined tiers: all, {', '.join(sorted(tiers_map_dict))}",
                err=True,
            )
            raise typer.Exit(code=1)
        cases = discover_retrieval_case_dirs(path, tier=tier)
        if not cases:
            typer.echo(f"No retrieval cases found under {path}", err=True)
            raise typer.Exit(code=1)
        payload = run_suite_cli_flow(
            title="Retrieval benchmark suite",
            cases=cases,
            settings=settings,
            run_one=_run_one,
            summarize=_summarize,
            json_out=json_out,
            md_out=md_out,
            summary_from_reports=_retrieval_suite_summary,
        )
        if not bool(payload.get("summary", {}).get("all_passed", True)):
            raise typer.Exit(code=1)
        return

    report = _run_one(path)
    run_single_case_json_outputs(
        report=report,
        settings=settings,
        summarize=_summarize,
        json_out=json_out,
        md_out=md_out,
    )
    if not _is_passed(report):
        raise typer.Exit(code=1)


def main() -> None:
    """CLI entry for ``science-graphrag-retrieval-benchmark``."""

    typer.run(_cli)


if __name__ == "__main__":
    main()
