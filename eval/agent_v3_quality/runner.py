"""CLI suite runner: baseline vs candidate agent runtimes + pairwise judge."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer

from eval.agent_v3_quality.branch_outcome import aggregate_branch_outcomes
from eval.agent_v3_quality.case_loader import discover_agent_v3_quality_case_dirs
from eval.agent_v3_quality.contract import (
    BENCHMARK_FAMILY_SHORT,
    JUDGE_MODEL_FAMILY_IDS,
    LOGICAL_FAMILY_ID,
    REVIEW_VERSION,
    resolve_benchmark_judge_model,
)
from eval.agent_v3_quality.judge import judge_meta, judge_prompt_fingerprint
from eval.agent_v3_quality.judge_metrics import cost_delta_from_cases, summarize_suite
from eval.agent_v3_quality.runner_branches import (
    HEARTBEAT_ENV,
    PROGRESS_ENV,
    run_agent_branches_for_case,
)
from eval.agent_v3_quality.runner_report import render_suite_markdown, run_v3_quality_case
from eval.bench_common import benchmark_run_metadata
from science_graphrag.config import get_settings

# Backward-compatible constants for scripts/tests that still import ``runner``.
__all__ = [
    "HEARTBEAT_ENV",
    "PROGRESS_ENV",
    "main",
    "run_agent_branches_for_case",
    "run_v3_quality_case",
]


def _cli(  # pylint: disable=too-many-arguments,too-many-locals,too-many-positional-arguments
    path: Path = typer.Argument(..., exists=True, readable=True, help="Fixtures root"),
    suite: bool = typer.Option(False, "--suite"),
    tier: str = typer.Option("judge_mini", "--tier"),
    baseline_runtime: str = typer.Option("langgraph_research_v1", "--baseline-runtime"),
    candidate_runtime: str = typer.Option("langgraph_supervisor_v3", "--candidate-runtime"),
    transport: str = typer.Option(
        "subprocess",
        "--transport",
        help=(
            "subprocess: isolated python -m one_shot per runtime; "
            "http: POST /v2/agent/query (single server runtime)."
        ),
    ),
    api_base_url: str | None = typer.Option(
        None,
        "--api-base-url",
        help="Required when --transport http (e.g. http://127.0.0.1:18787).",
    ),
    candidate_api_base_url: str | None = typer.Option(
        None,
        "--candidate-api-base-url",
        help="Optional second API base for candidate (http transport).",
    ),
    allow_http_single_base: bool = typer.Option(
        False,
        "--allow-http-single-base",
        help=(
            "Allow http mode with one API base (both branches read same server/runtime). "
            "Use only for smoke checks."
        ),
    ),
    mock_agent: bool = typer.Option(
        False,
        "--mock-agent",
        help="Deterministic stub answers (CI / contract smoke without live stack).",
    ),
    llm_judge: bool = typer.Option(
        False,
        "--llm-judge",
        help=(
            "Use extraction LLM for rubric judge "
            "(requires SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY)."
        ),
    ),
    progress: bool = typer.Option(
        False,
        "--progress",
        help=(
            "Log per-case stderr phases (baseline/candidate/judge). "
            f"Also enabled when {PROGRESS_ENV}=1."
        ),
    ),
    max_tool_calls: int = typer.Option(12, "--max-tool-calls"),
    subprocess_timeout_s: float = typer.Option(600.0, "--subprocess-timeout-s"),
    judge_model: str | None = typer.Option(
        None,
        "--judge-model",
        help="Override chat model id for the pairwise LLM judge (OpenRouter-style id).",
    ),
    judge_model_family: str | None = typer.Option(
        None,
        "--judge-model-family",
        help=(
            "Preset judge backbone: deepseek | anthropic | openai "
            "(env SCIENCE_GRAPHRAG_AGENT_V3_QUALITY_JUDGE_MODEL_<FAMILY> overrides defaults; "
            "mutually exclusive with --judge-model)."
        ),
    ),
    seeds: int = typer.Option(
        1,
        "--seeds",
        min=1,
        help=(
            "Wave F2: judge passes. When >1, agent branches run once per case, then only the "
            "pairwise judge re-runs per seed (temperature/seed sweep)."
        ),
    ),
    json_out: Path | None = typer.Option(None, "--json-out"),
    md_out: Path | None = typer.Option(None, "--md-out"),
    case: str | None = typer.Option(None, "--case", help="Run a single case directory name"),
    max_cases: int | None = typer.Option(None, "--max-cases"),
) -> None:
    settings = get_settings()
    if not suite:
        raise typer.BadParameter("Only --suite mode is supported for this benchmark.")

    if (judge_model or "").strip() and (judge_model_family or "").strip():
        raise typer.BadParameter("Use only one of --judge-model or --judge-model-family")
    fam_key = (judge_model_family or "").strip().lower()
    if fam_key and fam_key not in JUDGE_MODEL_FAMILY_IDS:
        raise typer.BadParameter(
            f"--judge-model-family must be one of {sorted(JUDGE_MODEL_FAMILY_IDS)}; got {fam_key!r}",
        )
    resolved_judge = resolve_benchmark_judge_model(
        judge_model=judge_model,
        judge_model_family=judge_model_family,
    )

    cases = discover_agent_v3_quality_case_dirs(path, tier=tier)
    if case:
        cases = [c for c in cases if c.name == case]
    if max_cases is not None:
        cases = cases[: max(0, max_cases)]
    if not cases:
        typer.echo("No cases discovered for tier.", err=True)
        raise typer.Exit(code=1)

    if transport == "http" and not mock_agent and not api_base_url:
        typer.echo("--api-base-url is required for --transport http", err=True)
        raise typer.Exit(code=1)

    n_seeds = max(1, int(seeds))
    reports: list[dict[str, Any]]
    multiseed_block: dict[str, Any] | None = None

    if n_seeds == 1:
        reports = []
        for case_path in cases:
            reports.append(
                run_v3_quality_case(
                    case_path,
                    baseline_runtime=baseline_runtime,
                    candidate_runtime=candidate_runtime,
                    mock_agent=mock_agent,
                    transport=transport,
                    api_base_url=api_base_url,
                    candidate_api_base_url=candidate_api_base_url,
                    allow_http_single_base=allow_http_single_base,
                    max_tool_calls=max_tool_calls,
                    subprocess_timeout_s=subprocess_timeout_s,
                    llm_judge=llm_judge,
                    progress=progress,
                    judge_seed=None,
                    judge_model=resolved_judge,
                ),
            )
    else:
        prepared: list[
            tuple[
                Path,
                tuple[
                    dict[str, Any],
                    str,
                    str,
                    str | None,
                    dict[str, Any],
                    dict[str, Any],
                    list[str],
                    dict[str, float],
                ],
            ]
        ] = []
        for case_path in cases:
            tup = run_agent_branches_for_case(
                case_path,
                baseline_runtime=baseline_runtime,
                candidate_runtime=candidate_runtime,
                mock_agent=mock_agent,
                transport=transport,
                api_base_url=api_base_url,
                candidate_api_base_url=candidate_api_base_url,
                allow_http_single_base=allow_http_single_base,
                max_tool_calls=max_tool_calls,
                subprocess_timeout_s=subprocess_timeout_s,
                progress=progress,
            )
            prepared.append((case_path, tup))

        per_seed_meta: list[dict[str, Any]] = []
        last_reports: list[dict[str, Any]] = []
        for seed_idx in range(n_seeds):
            last_reports = []
            for case_path, tup in prepared:
                last_reports.append(
                    run_v3_quality_case(
                        case_path,
                        baseline_runtime=baseline_runtime,
                        candidate_runtime=candidate_runtime,
                        mock_agent=mock_agent,
                        transport=transport,
                        api_base_url=api_base_url,
                        candidate_api_base_url=candidate_api_base_url,
                        allow_http_single_base=allow_http_single_base,
                        max_tool_calls=max_tool_calls,
                        subprocess_timeout_s=subprocess_timeout_s,
                        llm_judge=llm_judge,
                        progress=progress,
                        judge_seed=seed_idx,
                        judge_model=resolved_judge,
                        prepared_branches=tup,
                    ),
                )
            summ = summarize_suite(last_reports)
            summ.update(aggregate_branch_outcomes(last_reports))
            cd_seed = cost_delta_from_cases(last_reports)
            if cd_seed:
                summ["cost_delta"] = cd_seed
            per_seed_meta.append(
                {
                    "seed_index": seed_idx,
                    "mean_delta": summ.get("mean_delta"),
                    "pairwise_candidate_win_rate": summ.get("pairwise_candidate_win_rate"),
                    "cost_delta": summ.get("cost_delta"),
                },
            )
        reports = last_reports
        mean_deltas = [
            float(x["mean_delta"])
            for x in per_seed_meta
            if isinstance(x.get("mean_delta"), (int, float))
        ]
        rollup: dict[str, Any] = {"per_seed": per_seed_meta}
        if mean_deltas:
            srt = sorted(mean_deltas)
            mid = len(srt) // 2
            if len(srt) % 2 == 1:
                med = float(srt[mid])
            else:
                med = (float(srt[mid - 1]) + float(srt[mid])) / 2.0
            rollup.update(
                {
                    "mean_delta_min": round(min(mean_deltas), 4),
                    "mean_delta_max": round(max(mean_deltas), 4),
                    "mean_delta_median": round(med, 4),
                    "mean_delta_spread": round(max(mean_deltas) - min(mean_deltas), 4),
                },
            )
        multiseed_block = rollup

    summary = summarize_suite(reports)
    summary.update(aggregate_branch_outcomes(reports))
    cd = cost_delta_from_cases(reports)
    if cd:
        summary["cost_delta"] = cd
    if multiseed_block is not None:
        summary["multiseed"] = multiseed_block
    meta = benchmark_run_metadata(settings)
    meta.update(
        {
            "logical_family_id": LOGICAL_FAMILY_ID,
            "benchmark_family_short": BENCHMARK_FAMILY_SHORT,
            "tier": tier,
            "baseline_runtime": baseline_runtime,
            "candidate_runtime": candidate_runtime,
            "transport": transport,
            "mock_agent": mock_agent,
            "seeds": n_seeds,
            **judge_meta(llm=llm_judge, judge_model_override=resolved_judge),
            "judge_prompt_fingerprint": judge_prompt_fingerprint(),
        },
    )
    payload: dict[str, Any] = {
        "review_version": REVIEW_VERSION,
        "family": BENCHMARK_FAMILY_SHORT,
        "tier": tier,
        "baseline_runtime": baseline_runtime,
        "candidate_runtime": candidate_runtime,
        "run_metadata": meta,
        "summary": summary,
        "cases": reports,
    }

    md_full = render_suite_markdown(tier=tier, n_seeds=n_seeds, summary=summary, reports=reports)
    typer.echo(md_full)
    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        typer.echo(f"Wrote JSON suite report to {json_out}", err=True)
    if md_out:
        md_out.parent.mkdir(parents=True, exist_ok=True)
        md_out.write_text(md_full, encoding="utf-8")
        typer.echo(f"Wrote Markdown suite summary to {md_out}", err=True)

    if not summary.get("all_passed", False):
        raise typer.Exit(code=1)


def main() -> None:
    """Console entrypoint for ``science-graphrag-agent-v3-quality-benchmark``."""

    typer.run(_cli)


if __name__ == "__main__":
    main()
