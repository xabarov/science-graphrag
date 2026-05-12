"""CLI suite runner: baseline vs candidate agent runtimes + pairwise judge."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx
import typer

from eval.agent_v3_quality.branch_outcome import (
    aggregate_branch_outcomes,
    branch_outcome_from_branch,
)
from eval.agent_v3_quality.case_loader import (
    discover_agent_v3_quality_case_dirs,
    load_case_gold,
    load_case_question,
)
from eval.agent_v3_quality.contract import (
    BENCHMARK_FAMILY_SHORT,
    JUDGE_MODEL_FAMILY_IDS,
    LOGICAL_FAMILY_ID,
    REVIEW_VERSION,
    resolve_benchmark_judge_model,
)
from eval.agent_v3_quality.judge import (
    judge_meta,
    judge_prompt_fingerprint,
    run_pairwise_judge_for_case,
)
from eval.agent_v3_quality.judge_metrics import cost_delta_from_cases, summarize_suite
from eval.bench_common import benchmark_run_metadata
from science_graphrag.artifacts.benchmark_paths import REPO_ROOT
from science_graphrag.config import get_settings

PROGRESS_ENV = "SCIENCE_GRAPHRAG_AGENT_V3_QUALITY_PROGRESS"
HEARTBEAT_ENV = "SCIENCE_GRAPHRAG_AGENT_V3_QUALITY_HEARTBEAT_S"
DEFAULT_SUBPROCESS_HEARTBEAT_S = 20.0


def _progress_enabled(explicit: bool) -> bool:
    if explicit:
        return True
    return (os.environ.get(PROGRESS_ENV) or "").strip().lower() in {"1", "true", "yes"}


def _progress_log(case_id: str, phase: str, **fields: Any) -> None:
    """Stderr line for live suite runs (``--progress`` or env)."""

    extra = " ".join(f"{k}={fields[k]!r}" for k in sorted(fields))
    line = f"[agent_v3_quality] case={case_id} phase={phase}"
    if extra:
        line += f" {extra}"
    print(line, file=sys.stderr, flush=True)


def _agent_live_headers() -> dict[str, str]:
    """Optional auth headers (same contract as ``scripts/live_check/http_suite``)."""

    out: dict[str, str] = {}
    auth = (os.environ.get("AGENT_LIVE_AUTHORIZATION") or "").strip()
    if auth:
        out["Authorization"] = auth
    admin = (os.environ.get("AGENT_LIVE_ADMIN_KEY") or "").strip()
    if admin:
        out["X-Admin-Key"] = admin
    return out


def _tool_trace_summary(tool_trace: list[Any], *, max_steps: int = 24) -> str:
    names: list[str] = []
    for step in tool_trace[:max_steps]:
        if isinstance(step, dict):
            t = step.get("tool")
            if t:
                names.append(str(t))
    return " → ".join(names) if names else ""


def _branch_from_agent_payload(
    data: dict[str, Any],
    *,
    runtime_label: str,
    error: str | None = None,
) -> dict[str, Any]:
    rm = data.get("run_metadata") if isinstance(data.get("run_metadata"), dict) else {}
    usage = rm.get("usage") if isinstance(rm.get("usage"), dict) else {}
    total_tokens = usage.get("total_tokens")
    trace = data.get("tool_trace") if isinstance(data.get("tool_trace"), list) else []
    return {
        "answer": str(data.get("answer") or ""),
        "citations": data.get("citations") if isinstance(data.get("citations"), list) else [],
        "warnings": data.get("warnings") if isinstance(data.get("warnings"), list) else [],
        "tool_trace": trace,
        "tool_trace_summary": _tool_trace_summary(trace),
        "run_metadata": rm,
        "usage_total_tokens": total_tokens,
        "latency_ms": data.get("duration_ms"),
        "agent_runtime_label": str(rm.get("agent_runtime") or runtime_label),
        "error": error,
    }


def _run_subprocess_agent(
    runtime: str,
    question: str,
    workspace_id: str | None,
    max_tool_calls: int,
    *,
    timeout_s: float,
    heartbeat_s: float | None = None,
) -> dict[str, Any]:
    req = {
        "question": question,
        "workspace_id": workspace_id,
        "max_tool_calls": max_tool_calls,
    }
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        json.dump(req, tmp)
        tmp_path = tmp.name
    try:
        cmd = [
            sys.executable,
            "-m",
            "eval.agent_v3_quality.one_shot",
            runtime,
            tmp_path,
        ]
        child_env = os.environ.copy()
        if isinstance(heartbeat_s, (int, float)) and heartbeat_s > 0:
            child_env[HEARTBEAT_ENV] = str(float(heartbeat_s))
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=timeout_s,
            check=False,
            env=child_env,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "error": f"subprocess_timeout_after_{timeout_s}s: {exc}",
            "timeout_seconds": timeout_s,
        }
    try:
        raw = (proc.stdout or "").strip()
        if proc.returncode != 0:
            err = (proc.stderr or "")[:2000] or raw[:500]
            return {"error": f"subprocess_exit_{proc.returncode}: {err}"}
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            return {"error": f"subprocess_bad_json: {exc}: {raw[:500]}"}
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _run_http_agent(
    api_base: str,
    question: str,
    workspace_id: str | None,
    *,
    timeout_s: float,
) -> dict[str, Any]:
    url = f"{api_base.rstrip('/')}/v2/agent/query"
    payload: dict[str, Any] = {"question": question}
    if workspace_id:
        payload["workspace_id"] = workspace_id
    try:
        with httpx.Client(timeout=httpx.Timeout(timeout_s)) as client:
            r = client.post(
                url,
                json=payload,
                headers={"Accept": "application/json", **_agent_live_headers()},
            )
            r.raise_for_status()
            data = r.json()
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(data, dict):
        return {"error": "non_object_json"}
    return data


def _mock_branches(
    case_id: str, baseline_runtime: str, candidate_runtime: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    b_ans = f"[mock_baseline:{baseline_runtime}] Summary for {case_id} (ReAct-style stub)."
    c_ans = (
        f"[mock_candidate:{candidate_runtime}] Summary for {case_id} "
        f"(supervisor-style stub with synthesis and citations placeholder)."
    )
    baseline = {
        "answer": b_ans,
        "citations": [{"work_id": f"mock-baseline-{case_id}"}],
        "warnings": [],
        "tool_trace": [{"tool": "idea_search"}, {"tool": "final_answer"}],
        "tool_trace_summary": "idea_search → final_answer",
        "run_metadata": {"agent_runtime": baseline_runtime, "usage": {"total_tokens": 100}},
        "usage_total_tokens": 100,
        "latency_ms": 50,
        "agent_runtime_label": baseline_runtime,
        "error": None,
    }
    candidate = {
        "answer": c_ans,
        "citations": [{"work_id": f"mock-candidate-{case_id}"}],
        "warnings": [],
        "tool_trace": [{"tool": "route_to_specialist"}, {"tool": "final_answer"}],
        "tool_trace_summary": "route_to_specialist → final_answer",
        "run_metadata": {"agent_runtime": candidate_runtime, "usage": {"total_tokens": 180}},
        "usage_total_tokens": 180,
        "latency_ms": 120,
        "agent_runtime_label": candidate_runtime,
        "error": None,
    }
    return baseline, candidate


def run_agent_branches_for_case(  # pylint: disable=too-many-arguments,too-many-locals,too-many-branches,too-many-statements
    case_dir: Path,
    *,
    baseline_runtime: str,
    candidate_runtime: str,
    mock_agent: bool,
    transport: str,
    api_base_url: str | None,
    candidate_api_base_url: str | None = None,
    allow_http_single_base: bool = False,
    max_tool_calls: int,
    subprocess_timeout_s: float,
    progress: bool = False,
) -> tuple[
    dict[str, Any],
    str,
    str,
    str | None,
    dict[str, Any],
    dict[str, Any],
    list[str],
    dict[str, float],
]:
    """Run baseline and candidate agent branches only (no pairwise judge).

    Returns ``(gold, question, case_id, workspace_id, baseline, candidate, notes, timings)``
    where ``timings`` includes ``baseline_wall_s`` / ``candidate_wall_s`` when applicable.
    """

    gold = load_case_gold(case_dir)
    question = load_case_question(case_dir)
    case_id = case_dir.name
    ws_raw = gold.get("workspace_id")
    workspace_id = str(ws_raw).strip() if ws_raw not in (None, "", "null") else None

    prog = _progress_enabled(progress)

    notes: list[str] = []
    timings: dict[str, float] = {}
    if mock_agent:
        baseline, candidate = _mock_branches(case_id, baseline_runtime, candidate_runtime)
    elif transport == "http":
        if not api_base_url:
            raise ValueError("api_base_url required for transport=http")
        cand_base = (candidate_api_base_url or api_base_url).strip()
        same_base = cand_base.rstrip("/") == api_base_url.rstrip("/")
        if same_base and not allow_http_single_base:
            raise ValueError(
                "http transport requires two distinct API bases for real pairwise compare; "
                "pass --candidate-api-base-url (preferred) or explicitly allow this mode via "
                "--allow-http-single-base",
            )
        if prog:
            _progress_log(case_id, "baseline_start", branch="baseline", runtime=baseline_runtime)
        t_b0 = perf_counter()
        b_data = _run_http_agent(
            api_base_url, question, workspace_id, timeout_s=subprocess_timeout_s
        )
        timings["baseline_wall_s"] = round(perf_counter() - t_b0, 3)
        if prog:
            _progress_log(
                case_id,
                "baseline_done",
                branch="baseline",
                elapsed_s=timings["baseline_wall_s"],
                has_error=bool(b_data.get("error")),
            )
        if same_base:
            notes.append(
                "transport_http_single_base: baseline and candidate hit the same server; "
                "runtime differs only if you recreate API with different "
                "SCIENCE_GRAPHRAG_AGENT_RUNTIME or pass --candidate-api-base-url.",
            )
            c_data = copy.deepcopy(b_data)
            timings["candidate_wall_s"] = 0.0
            if prog:
                _progress_log(
                    case_id,
                    "candidate_skipped",
                    reason="http_single_base_deepcopy",
                    elapsed_s=0.0,
                )
        else:
            if prog:
                _progress_log(
                    case_id,
                    "candidate_start",
                    branch="candidate",
                    runtime=candidate_runtime,
                )
            t_c0 = perf_counter()
            c_data = _run_http_agent(
                cand_base, question, workspace_id, timeout_s=subprocess_timeout_s
            )
            timings["candidate_wall_s"] = round(perf_counter() - t_c0, 3)
            if prog:
                _progress_log(
                    case_id,
                    "candidate_done",
                    branch="candidate",
                    elapsed_s=timings["candidate_wall_s"],
                    has_error=bool(c_data.get("error")),
                )
        baseline = _branch_from_agent_payload(
            b_data, runtime_label=baseline_runtime, error=b_data.get("error")
        )
        candidate = _branch_from_agent_payload(
            c_data, runtime_label=candidate_runtime, error=c_data.get("error")
        )
    else:

        def _pack_subprocess(raw: dict[str, Any], runtime_label: str) -> dict[str, Any]:
            err = str(raw.get("error") or "").strip() or None
            if err:
                br = _branch_from_agent_payload({}, runtime_label=runtime_label, error=err)
                if raw.get("answer"):
                    br["answer"] = str(raw.get("answer") or "")
                return br
            return _branch_from_agent_payload(raw, runtime_label=runtime_label)

        if prog:
            _progress_log(case_id, "baseline_start", branch="baseline", runtime=baseline_runtime)
        t_b0 = perf_counter()
        b_raw = _run_subprocess_agent(
            baseline_runtime,
            question,
            workspace_id,
            max_tool_calls,
            timeout_s=subprocess_timeout_s,
            heartbeat_s=(DEFAULT_SUBPROCESS_HEARTBEAT_S if prog else None),
        )
        timings["baseline_wall_s"] = round(perf_counter() - t_b0, 3)
        if prog:
            _progress_log(
                case_id,
                "baseline_done",
                branch="baseline",
                elapsed_s=timings["baseline_wall_s"],
                has_error=bool((b_raw.get("error") or "").strip()),
            )
        if prog:
            _progress_log(case_id, "candidate_start", branch="candidate", runtime=candidate_runtime)
        t_c0 = perf_counter()
        c_raw = _run_subprocess_agent(
            candidate_runtime,
            question,
            workspace_id,
            max_tool_calls,
            timeout_s=subprocess_timeout_s,
            heartbeat_s=(DEFAULT_SUBPROCESS_HEARTBEAT_S if prog else None),
        )
        timings["candidate_wall_s"] = round(perf_counter() - t_c0, 3)
        if prog:
            _progress_log(
                case_id,
                "candidate_done",
                branch="candidate",
                elapsed_s=timings["candidate_wall_s"],
                has_error=bool((c_raw.get("error") or "").strip()),
            )
        baseline = _pack_subprocess(b_raw, baseline_runtime)
        candidate = _pack_subprocess(c_raw, candidate_runtime)

    return gold, question, case_id, workspace_id, baseline, candidate, notes, timings


def _quality_row_from_judged(
    *,
    gold: dict[str, Any],
    question: str,
    case_id: str,
    workspace_id: str | None,
    baseline_runtime: str,
    candidate_runtime: str,
    transport: str,
    mock_agent: bool,
    notes: list[str],
    timings: dict[str, float],
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    judged: dict[str, Any],
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "case_id": case_id,
        "family": gold.get("family"),
        "question": question,
        "workspace_id": workspace_id,
        "baseline_runtime": baseline_runtime,
        "candidate_runtime": candidate_runtime,
        "transport": transport,
        "mock_agent": mock_agent,
        "notes": notes,
        "timings": timings,
        "baseline": judged["baseline"],
        "candidate": judged["candidate"],
        "pairwise": judged["pairwise"],
        "passed": judged["passed"],
        "baseline_outcome": branch_outcome_from_branch(judged["baseline"]),
        "candidate_outcome": branch_outcome_from_branch(judged["candidate"]),
    }
    err_note = baseline.get("error") or candidate.get("error")
    if err_note:
        row["execution_error"] = err_note
    return row


def run_v3_quality_case(  # pylint: disable=too-many-arguments,too-many-locals
    case_dir: Path,
    *,
    baseline_runtime: str,
    candidate_runtime: str,
    mock_agent: bool,
    transport: str,
    api_base_url: str | None,
    candidate_api_base_url: str | None = None,
    allow_http_single_base: bool = False,
    max_tool_calls: int,
    subprocess_timeout_s: float,
    llm_judge: bool,
    progress: bool = False,
    judge_seed: int | None = None,
    judge_model: str | None = None,
    prepared_branches: (
        tuple[
            dict[str, Any],
            str,
            str,
            str | None,
            dict[str, Any],
            dict[str, Any],
            list[str],
            dict[str, float],
        ]
        | None
    ) = None,
) -> dict[str, Any]:
    """Execute baseline and candidate branches, then attach pairwise judge output."""

    prog = _progress_enabled(progress)
    t_case0 = perf_counter()
    if prog:
        _progress_log(
            case_dir.name,
            "case_start",
            transport=transport,
            mock_agent=mock_agent,
        )

    if prepared_branches is not None:
        gold, question, case_id, workspace_id, baseline, candidate, notes, timings = (
            prepared_branches
        )
    else:
        gold, question, case_id, workspace_id, baseline, candidate, notes, timings = (
            run_agent_branches_for_case(
                case_dir,
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
        )

    if prog:
        _progress_log(case_id, "judge_start", llm_judge=llm_judge, judge_seed=judge_seed)
    t_j0 = perf_counter()
    judged = run_pairwise_judge_for_case(
        question=question,
        gold=gold,
        baseline=baseline,
        candidate=candidate,
        use_llm=llm_judge,
        judge_model=judge_model,
        judge_seed=judge_seed,
    )
    timings = dict(timings)
    timings["judge_wall_s"] = round(perf_counter() - t_j0, 3)
    timings["case_wall_s"] = round(perf_counter() - t_case0, 3)
    if prog:
        _progress_log(
            case_id,
            "judge_done",
            elapsed_s=timings["judge_wall_s"],
            passed=judged["passed"],
            winner=(judged.get("pairwise") or {}).get("winner"),
        )
        _progress_log(case_id, "case_done", elapsed_s=timings["case_wall_s"])

    return _quality_row_from_judged(
        gold=gold,
        question=question,
        case_id=case_id,
        workspace_id=workspace_id,
        baseline_runtime=baseline_runtime,
        candidate_runtime=candidate_runtime,
        transport=transport,
        mock_agent=mock_agent,
        notes=notes,
        timings=timings,
        baseline=baseline,
        candidate=candidate,
        judged=judged,
    )


def _summarize_case(row: dict[str, Any]) -> str:
    """Markdown fragment for one suite row."""

    cid = row.get("case_id")
    pw = row.get("pairwise") or {}
    passed = row.get("passed")
    frag = {
        "pairwise": pw,
        "baseline_outcome": row.get("baseline_outcome"),
        "candidate_outcome": row.get("candidate_outcome"),
        "timings": row.get("timings"),
        "latency_ms": {
            "baseline": (row.get("baseline") or {}).get("latency_ms"),
            "candidate": (row.get("candidate") or {}).get("latency_ms"),
        },
        "usage_total_tokens": {
            "baseline": (row.get("baseline") or {}).get("usage_total_tokens"),
            "candidate": (row.get("candidate") or {}).get("usage_total_tokens"),
        },
    }
    if row.get("execution_error"):
        frag["execution_error"] = row.get("execution_error")
    return (
        f"## {cid} — {'PASS' if passed else 'FAIL'}\n\n"
        f"winner={pw.get('winner')} confidence={pw.get('confidence')}\n\n"
        f"```json\n{json.dumps(frag, indent=2)}\n```\n"
    )


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

    md_body = "\n\n---\n\n".join(_summarize_case(r) for r in reports)
    md_full = (
        f"# Agent v3 quality judge — {tier}\n\n"
        f"Cases: {len(reports)}  seeds: {n_seeds}\n\n"
        f"```json\n{json.dumps(summary, indent=2)}\n```\n\n" + md_body
    )
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
