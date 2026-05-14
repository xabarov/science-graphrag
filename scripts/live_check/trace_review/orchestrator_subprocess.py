"""Subprocess-backed trace-review stages (HTTP suite, E2E, Phoenix, compaction)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .orchestrator_env import compaction_in_turn_heartbeat_sec
from .orchestrator_paths import REPO_ROOT, SCRIPT_DIR


def run_http_suite(
    *,
    base_url: str,
    workspace_id: str | None,
    timeout: float,
    skip_sse: bool,
    skip_multi_turn: bool,
    extended_safety: bool = False,
) -> list[dict[str, Any]]:
    from http_suite import (  # pylint: disable=import-outside-toplevel,import-error
        CheckResult,
        run_default_suite,
    )

    out: list[dict[str, Any]] = []
    for res in run_default_suite(
        base_url,
        workspace_id=workspace_id,
        timeout=timeout,
        skip_sse=skip_sse,
        skip_multi_turn=skip_multi_turn,
        extended_safety=extended_safety,
    ):
        obj = asdict(res) if isinstance(res, CheckResult) else dict(res)
        out.append(obj)
    return out


def run_optional_e2e(
    args: argparse.Namespace,
    report_json_path: Path | None,
    *,
    subprocess_timeout: float | None = None,
) -> dict[str, Any] | None:
    if args.skip_e2e:
        return None
    out_json = args.e2e_json or (REPO_ROOT / "eval" / "results" / "trace_review_e2e_report.jsonl")
    cmd = [
        str(REPO_ROOT / ".venv" / "bin" / "python"),
        str(SCRIPT_DIR / "agent_od_workspace_e2e_audit.py"),
        "--suite",
        args.suite,
        "--timeout",
        str(args.timeout),
        "--write-report",
        str(out_json),
    ]
    if report_json_path:
        cmd.extend(["--write-report-json", str(report_json_path)])
    if args.with_trace_audit:
        cmd.append("--trace-audit")
    if not args.with_phoenix:
        cmd.append("--skip-phoenix")
    if not args.with_db_audit:
        cmd.append("--skip-postgres")

    env = os.environ.copy()
    env["AGENT_LIVE_BASE"] = args.base_url
    run_kw: dict[str, Any] = {"capture_output": True, "text": True, "env": env, "check": False}
    if subprocess_timeout is not None:
        run_kw["timeout"] = float(subprocess_timeout)
    try:
        completed = subprocess.run(cmd, **run_kw)
    except subprocess.TimeoutExpired as exc:
        out_tail = (exc.stdout or "")[-4000:]
        err_tail = (exc.stderr or "")[-4000:]
        return {
            "ok": False,
            "returncode": -1,
            "command": cmd,
            "stdout_tail": out_tail,
            "stderr_tail": err_tail or "subprocess.TimeoutExpired",
            "report_path": str(out_json),
            "full_report_json_path": str(report_json_path) if report_json_path else None,
            "timeout_expired": True,
            "timeout_sec": float(subprocess_timeout) if subprocess_timeout is not None else None,
        }
    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "command": cmd,
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
        "report_path": str(out_json),
        "full_report_json_path": str(report_json_path) if report_json_path else None,
    }


def run_phoenix_pull(trace_ids: list[str], out_jsonl: Path, timeout: float) -> dict[str, Any]:
    if not trace_ids:
        return {"ok": True, "skipped": True, "reason": "no_trace_ids"}
    cmd = [
        str(REPO_ROOT / ".venv" / "bin" / "python"),
        str(SCRIPT_DIR / "phoenix_trace_pull.py"),
        "--out-jsonl",
        str(out_jsonl),
        "--timeout",
        str(timeout),
    ]
    for tid in trace_ids:
        cmd.extend(["--trace-id", tid])
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=os.environ.copy(),
            check=False,
            timeout=max(30.0, float(timeout) * 2),
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "returncode": -1,
            "path": str(out_jsonl),
            "stderr_tail": ((exc.stderr or "")[-2000:] or "subprocess.TimeoutExpired"),
            "timeout_expired": True,
        }
    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "path": str(out_jsonl),
        "stderr_tail": completed.stderr[-2000:],
    }


def run_compaction_turn_review(
    *,
    base_url: str,
    workspace_id: str | None,
    timeout: float,
    turns: int,
    require_after: int,
    out_json: Path,
    emit_merged_into: Path | None,
    mode: str = "default",
    max_retries_per_turn: int = 0,
    heartbeat_sec: float | None = None,
    stage_heartbeat_cap_sec: float | None = None,
) -> dict[str, Any]:
    resolved_hb = compaction_in_turn_heartbeat_sec(mode=str(mode), override=heartbeat_sec)
    if stage_heartbeat_cap_sec is not None:
        resolved_hb = min(resolved_hb, max(5.0, float(stage_heartbeat_cap_sec)))
    cmd = [
        str(REPO_ROOT / ".venv" / "bin" / "python"),
        str(SCRIPT_DIR / "compaction_turn_review.py"),
        "--base-url",
        base_url.rstrip("/"),
        "--turns",
        str(turns),
        "--require-compaction-after",
        str(require_after),
        "--timeout",
        str(timeout),
        "--heartbeat-sec",
        str(resolved_hb),
        "--out-json",
        str(out_json),
        "--out-md",
        str(out_json.with_suffix(".md")),
        "--mode",
        str(mode),
        "--max-retries-per-turn",
        str(max(0, int(max_retries_per_turn))),
    ]
    if workspace_id:
        cmd.extend(["--workspace-id", workspace_id])
    if emit_merged_into:
        cmd.extend(["--emit-merged-into", str(emit_merged_into)])
    attempts_per_turn = max(1.0, 1.0 + float(max(0, int(max_retries_per_turn))))
    wall_budget = max(
        120.0,
        float(timeout) * float(max(1, int(turns))) * attempts_per_turn * 1.25,
    )
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=os.environ.copy(),
            check=False,
            timeout=wall_budget,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "returncode": -1,
            "path": str(out_json),
            "stdout_tail": ((exc.stdout or "")[-2000:] or ""),
            "stderr_tail": ((exc.stderr or "")[-2000:] or "subprocess.TimeoutExpired"),
            "timeout_expired": True,
            "failure_reason": "compaction_turn_review_timeout",
        }
    report_blob: dict[str, Any] = {}
    if out_json.exists():
        try:
            report_blob = json.loads(out_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            report_blob = {}
    failure_reason: str | None = None
    top_raw = report_blob.get("failure_reason")
    if isinstance(top_raw, str) and top_raw.strip():
        failure_reason = top_raw.strip()
    elif isinstance(report_blob.get("verdict"), dict):
        reasons = report_blob["verdict"].get("reasons") or []
        if isinstance(reasons, list) and reasons:
            failure_reason = str(reasons[0])
    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "path": str(out_json),
        "stdout_tail": completed.stdout[-2000:],
        "stderr_tail": completed.stderr[-2000:],
        "failure_reason": failure_reason,
        "failed_turn": report_blob.get("failed_turn") if isinstance(report_blob, dict) else None,
        "failure_kind": report_blob.get("failure_kind") if isinstance(report_blob, dict) else None,
    }
