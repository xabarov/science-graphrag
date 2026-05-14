"""Baseline/candidate branch execution for ``agent_v3_quality`` (subprocess + http)."""

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

from eval.agent_v3_quality.case_loader import load_case_gold, load_case_question
from science_graphrag.artifacts.benchmark_paths import REPO_ROOT

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
