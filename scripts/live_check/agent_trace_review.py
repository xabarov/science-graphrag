#!/usr/bin/env python3
"""Canonical live trace-review orchestrator (trace-review-v1).

Runs base HTTP checks plus optional OD E2E audit and emits a single JSON/MD
artifact pair suitable for PR evidence and baseline diff.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent.parent


def _runtime_attribution_from_env() -> tuple[str | None, str | None]:
    runtime = str(os.environ.get("SCIENCE_GRAPHRAG_AGENT_RUNTIME") or "").strip()
    if runtime in {"retrieval_v1", "langgraph_research_v1"}:
        return "single_agent_research", "single_agent_react"
    if runtime == "langgraph_supervisor_v1":
        return "supervisor_specialists", "supervisor_graph"
    return None, None


def _runtime_attribution_from_runtime_id(runtime_id: Any) -> tuple[str | None, str | None]:
    rt = str(runtime_id or "").strip()
    if rt in {"retrieval_v1", "langgraph_research_v1"}:
        return "single_agent_research", "single_agent_react"
    if rt == "langgraph_supervisor_v1":
        return "supervisor_specialists", "supervisor_graph"
    return None, None


def _ensure_local_imports() -> None:
    if str(_SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPT_DIR))
    eval_root = _REPO_ROOT / "eval"
    if str(eval_root) not in sys.path:
        sys.path.insert(0, str(eval_root))


def _load_dotenv(env_file: Path) -> None:
    from dotenv_util import (  # pylint: disable=import-outside-toplevel,import-error
        load_dotenv_or_warn,
    )

    load_dotenv_or_warn(env_file)


def _run_http_suite(
    *,
    base_url: str,
    workspace_id: str | None,
    timeout: float,
    skip_sse: bool,
    skip_multi_turn: bool,
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
    ):
        obj = asdict(res) if isinstance(res, CheckResult) else dict(res)
        out.append(obj)
    return out


def _run_optional_e2e(
    args: argparse.Namespace, report_json_path: Path | None
) -> dict[str, Any] | None:
    if args.skip_e2e:
        return None
    out_json = args.e2e_json or (_REPO_ROOT / "eval" / "results" / "trace_review_e2e_report.jsonl")
    cmd = [
        str(_REPO_ROOT / ".venv" / "bin" / "python"),
        str(_SCRIPT_DIR / "agent_od_workspace_e2e_audit.py"),
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
    completed = subprocess.run(cmd, capture_output=True, text=True, env=env, check=False)
    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "command": cmd,
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
        "report_path": str(out_json),
        "full_report_json_path": str(report_json_path) if report_json_path else None,
    }


def _run_phoenix_pull(trace_ids: list[str], out_jsonl: Path, timeout: float) -> dict[str, Any]:
    if not trace_ids:
        return {"ok": True, "skipped": True, "reason": "no_trace_ids"}
    cmd = [
        str(_REPO_ROOT / ".venv" / "bin" / "python"),
        str(_SCRIPT_DIR / "phoenix_trace_pull.py"),
        "--out-jsonl",
        str(out_jsonl),
        "--timeout",
        str(timeout),
    ]
    for tid in trace_ids:
        cmd.extend(["--trace-id", tid])
    completed = subprocess.run(
        cmd, capture_output=True, text=True, env=os.environ.copy(), check=False
    )
    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "path": str(out_jsonl),
        "stderr_tail": completed.stderr[-2000:],
    }


def _run_compaction_turn_review(
    *,
    base_url: str,
    workspace_id: str | None,
    timeout: float,
    turns: int,
    require_after: int,
    out_json: Path,
    emit_merged_into: Path | None,
) -> dict[str, Any]:
    cmd = [
        str(_REPO_ROOT / ".venv" / "bin" / "python"),
        str(_SCRIPT_DIR / "compaction_turn_review.py"),
        "--base-url",
        base_url.rstrip("/"),
        "--turns",
        str(turns),
        "--require-compaction-after",
        str(require_after),
        "--timeout",
        str(timeout),
        "--out-json",
        str(out_json),
        "--out-md",
        str(out_json.with_suffix(".md")),
    ]
    if workspace_id:
        cmd.extend(["--workspace-id", workspace_id])
    if emit_merged_into:
        cmd.extend(["--emit-merged-into", str(emit_merged_into)])
    completed = subprocess.run(
        cmd, capture_output=True, text=True, env=os.environ.copy(), check=False
    )
    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "path": str(out_json),
        "stdout_tail": completed.stdout[-2000:],
        "stderr_tail": completed.stderr[-2000:],
    }


def _checks_dict(checks: list[dict[str, Any]]) -> dict[str, bool]:
    return {str(c.get("name")): bool(c.get("ok")) for c in checks if c.get("name")}


def _sse_missing_final(checks: list[dict[str, Any]]) -> bool:
    for c in checks:
        if c.get("name") == "agent_v2_sse" and "missing_final_answer" in str(c.get("detail") or ""):
            return True
    return False


def _write_markdown(path: Path, review_dict: dict[str, Any]) -> None:
    lines: list[str] = []
    lines.append("# Agent Trace Review")
    lines.append("")
    lines.append(f"- Generated: `{review_dict.get('generated_at')}`")
    ctx = review_dict.get("run_context") or {}
    lines.append(f"- Base URL: `{ctx.get('base_url')}`")
    lines.append(f"- Workspace: `{ctx.get('workspace_id')}`")
    lines.append(f"- Suite: `{ctx.get('suite')}`")
    if ctx.get("run_kind"):
        lines.append(f"- Run kind: `{ctx.get('run_kind')}`")
    if ctx.get("graph_id"):
        lines.append(f"- Graph id: `{ctx.get('graph_id')}`")
    if review_dict.get("phoenix_snapshot_path"):
        lines.append(f"- Phoenix snapshot: `{review_dict.get('phoenix_snapshot_path')}`")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    lines.append("| Check | OK | Detail |")
    lines.append("|------|----|--------|")
    for chk in review_dict.get("checks") or []:
        lines.append(
            f"| `{chk.get('name')}` | `{bool(chk.get('ok'))}` | {str(chk.get('detail') or '')[:180]} |"
        )
    lines.append("")

    tl = review_dict.get("trace_timeline") or []
    if tl:
        lines.append("## Trace timeline")
        lines.append("")
        lines.append(
            "| Case | Run kind | Graph id | Steps | last_tool | Phoenix missing | dur_ms | warnings |",
        )
        lines.append(
            "|------|----------|----------|-------|-----------|-----------------|--------|----------|"
        )
        for row in tl:
            steps = row.get("tool_steps") or []
            last_tool = steps[-1].get("tool") if steps else ""
            pa = row.get("phoenix_alignment") or {}
            miss_n = len(pa.get("missing") or []) if isinstance(pa, dict) else 0
            warns = row.get("warnings") or []
            wshort = ",".join(str(x)[:40] for x in warns[:2])
            lines.append(
                f"| `{row.get('case_id')}` | `{row.get('run_kind')}` | `{row.get('graph_id')}` "
                f"| {len(steps)} | `{last_tool}` | {miss_n} | "
                f"`{row.get('duration_ms')}` | {wshort[:80]} |",
            )
        lines.append("")

    lines.append("## Metrics")
    lines.append("")
    m = review_dict.get("metrics") or {}
    for k in sorted(m.keys()):
        lines.append(f"- `{k}`: `{m.get(k)}`")
    lines.append("")

    e2e = review_dict.get("e2e_audit")
    if isinstance(e2e, dict):
        lines.append("## E2E Audit")
        lines.append("")
        lines.append(f"- OK: `{bool(e2e.get('ok'))}`")
        lines.append(f"- Return code: `{e2e.get('returncode')}`")
        lines.append(f"- Report path: `{e2e.get('report_path')}`")
        if e2e.get("full_report_json_path"):
            lines.append(f"- Full JSON: `{e2e.get('full_report_json_path')}`")
        lines.append("")

    ph = review_dict.get("phoenix_pull")
    if isinstance(ph, dict) and not ph.get("skipped"):
        lines.append("## Phoenix pull")
        lines.append("")
        lines.append(f"- OK: `{ph.get('ok')}`")
        lines.append(f"- Path: `{ph.get('path')}`")
        lines.append("")

    cre = review_dict.get("compaction_turn_review")
    if isinstance(cre, dict):
        lines.append("## Compaction turn review")
        lines.append("")
        lines.append(f"- OK: `{cre.get('ok')}`")
        lines.append(f"- Path: `{cre.get('path')}`")
        lines.append("")

    verdict = review_dict.get("verdict") or {}
    lines.append("## Verdict")
    lines.append("")
    lines.append(f"- Status: `{verdict.get('status')}`")
    for reason in verdict.get("fail_reasons") or []:
        lines.append(f"- FAIL: {reason}")
    for reason in verdict.get("warn_reasons") or []:
        lines.append(f"- WARN: {reason}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url", default=os.environ.get("AGENT_LIVE_BASE", "http://127.0.0.1:8000")
    )
    parser.add_argument("--env-file", type=Path, default=_REPO_ROOT / ".env")
    parser.add_argument(
        "--workspace-id", default=os.environ.get("AGENT_LIVE_WORKSPACE_ID", "").strip() or None
    )
    parser.add_argument(
        "--timeout", type=float, default=float(os.environ.get("AGENT_LIVE_TIMEOUT_SEC", "240"))
    )
    parser.add_argument("--suite", choices=["default", "heavy", "full"], default="default")
    parser.add_argument(
        "--profile",
        choices=["quick", "default", "heavy"],
        default="default",
        help="Execution profile controlling default skip flags/timeouts.",
    )
    parser.add_argument("--skip-sse", action="store_true")
    parser.add_argument("--skip-multi-turn", action="store_true")
    parser.add_argument("--skip-e2e", action="store_true")
    parser.add_argument("--with-trace-audit", action="store_true")
    parser.add_argument("--with-phoenix", action="store_true")
    parser.add_argument("--with-db-audit", action="store_true")
    parser.add_argument(
        "--with-compaction-turns", type=int, default=0, help="If >0, run compaction_turn_review.py"
    )
    parser.add_argument(
        "--require-compaction-after",
        type=int,
        default=2,
        help="Threshold turn for compaction_turn_review (default 2)",
    )
    parser.add_argument(
        "--emit-merged-review",
        type=Path,
        default=None,
        help="Path for compaction_turn_review --emit-merged-into (default: --out-json)",
    )
    parser.add_argument(
        "--out-json", type=Path, default=_REPO_ROOT / "eval" / "results" / "trace-review.json"
    )
    parser.add_argument(
        "--out-md", type=Path, default=_REPO_ROOT / "eval" / "results" / "trace-review.md"
    )
    parser.add_argument("--e2e-json", type=Path, default=None)
    args = parser.parse_args()

    _ensure_local_imports()
    from trace_review_schema import (  # pylint: disable=import-outside-toplevel
        REVIEW_VERSION,
        TraceReviewV1,
        aggregate_metrics_from_timeline,
        check_from_dict,
        merge_e2e_report_json_into_review,
        trace_review_to_dict,
        verdict_from_signals,
    )

    _load_dotenv(args.env_file)
    if args.profile == "quick":
        args.skip_e2e = True
        args.skip_multi_turn = True
    elif args.profile == "heavy":
        args.with_trace_audit = True
        args.with_phoenix = True
        args.with_db_audit = True
        if args.suite == "default":
            args.suite = "heavy"

    checks = _run_http_suite(
        base_url=args.base_url.rstrip("/"),
        workspace_id=args.workspace_id,
        timeout=args.timeout,
        skip_sse=args.skip_sse,
        skip_multi_turn=args.skip_multi_turn,
    )

    report_json_path: Path | None = None
    if not args.skip_e2e:
        tmp = tempfile.NamedTemporaryFile(  # noqa: SIM115
            suffix=".json",
            delete=False,
            prefix="e2e_full_report_",
        )
        tmp.close()
        report_json_path = Path(tmp.name)

    e2e = _run_optional_e2e(args, report_json_path)

    trace_timeline = merge_e2e_report_json_into_review(cases=[], workspace_postgres=None)
    if report_json_path and report_json_path.exists() and not args.skip_e2e:
        try:
            report_obj = json.loads(report_json_path.read_text(encoding="utf-8"))
            cases = report_obj.get("cases") or []
            if isinstance(cases, list):
                postgres_blob = report_obj.get("postgres_ingest_jobs")
                trace_timeline = merge_e2e_report_json_into_review(
                    cases=[x for x in cases if isinstance(x, dict)],
                    workspace_postgres=postgres_blob if isinstance(postgres_blob, dict) else None,
                )
        except (OSError, json.JSONDecodeError):
            trace_timeline = merge_e2e_report_json_into_review(cases=[], workspace_postgres=None)

    phoenix_snap_path: str | None = None
    phoenix_pull_meta: dict[str, Any] | None = None
    if args.with_phoenix and report_json_path and report_json_path.exists() and not args.skip_e2e:
        try:
            report_obj = json.loads(report_json_path.read_text(encoding="utf-8"))
            tids: list[str] = []
            for c in report_obj.get("cases") or []:
                if not isinstance(c, dict):
                    continue
                tid = (c.get("phoenix_trace_id") or "").strip()
                if tid:
                    tids.append(tid)
            snap_path = args.out_json.parent / f"{args.out_json.stem}_phoenix_spans.jsonl"
            phoenix_pull_meta = _run_phoenix_pull(tids, snap_path, timeout=min(60.0, args.timeout))
            if snap_path.exists():
                phoenix_snap_path = str(snap_path)
        except (OSError, json.JSONDecodeError):
            phoenix_pull_meta = {"ok": False, "error": "report_parse_failed"}

    metrics = aggregate_metrics_from_timeline(trace_timeline)

    chk_map = _checks_dict(checks)
    required = frozenset({"health", "agent_v2_sync_json", "agent_v2_sse"})
    sse_bad = _sse_missing_final(checks)

    verdict_obj = verdict_from_signals(
        checks_ok=chk_map,
        required_checks=required,
        e2e_ok=None if e2e is None else bool(e2e.get("ok")),
        metrics=metrics,
        sse_missing_final_in_checks=sse_bad,
    )

    review = TraceReviewV1(
        review_version=REVIEW_VERSION,
        generated_at=datetime.now(UTC).isoformat(),
        run_context=None,
        checks=tuple(check_from_dict(x) for x in checks),
        trace_timeline=trace_timeline,
        metrics=metrics,
        verdict=verdict_obj,
        e2e_audit=e2e,
        phoenix_snapshot_path=phoenix_snap_path,
    )

    review_dict = trace_review_to_dict(review)
    run_kind, graph_id = _runtime_attribution_from_env()
    if report_json_path and report_json_path.exists() and (run_kind is None or graph_id is None):
        try:
            report_obj = json.loads(report_json_path.read_text(encoding="utf-8"))
            cases = report_obj.get("cases") or []
            if isinstance(cases, list):
                for case in cases:
                    if not isinstance(case, dict):
                        continue
                    rm = case.get("run_metadata") or {}
                    if not isinstance(rm, dict):
                        continue
                    rk = str(rm.get("run_kind") or "").strip() or None
                    gid = str(rm.get("graph_id") or "").strip() or None
                    if rk is None or gid is None:
                        drk, dgid = _runtime_attribution_from_runtime_id(rm.get("agent_runtime"))
                        rk = rk or drk
                        gid = gid or dgid
                    if rk or gid:
                        run_kind = run_kind or rk
                        graph_id = graph_id or gid
                        break
        except (OSError, json.JSONDecodeError):
            pass
    review_dict["run_context"] = {
        "base_url": args.base_url.rstrip("/"),
        "workspace_id": args.workspace_id,
        "suite": args.suite,
        "profile": args.profile,
        "run_kind": run_kind,
        "graph_id": graph_id,
        "feature_flags": {
            "agent_runtime": os.environ.get("SCIENCE_GRAPHRAG_AGENT_RUNTIME"),
            "agent_rule_tool_search_enabled": os.environ.get(
                "SCIENCE_GRAPHRAG_AGENT_RULE_TOOL_SEARCH_ENABLED"
            ),
            "agent_tool_search_deferred_schema_refs_enabled": os.environ.get(
                "SCIENCE_GRAPHRAG_AGENT_TOOL_SEARCH_DEFERRED_SCHEMA_REFS_ENABLED"
            ),
            "agent_budget_stop_reasoning_enabled": os.environ.get(
                "SCIENCE_GRAPHRAG_AGENT_BUDGET_STOP_REASONING_ENABLED"
            ),
            "agent_thread_insights_enabled": os.environ.get(
                "SCIENCE_GRAPHRAG_AGENT_THREAD_INSIGHTS_ENABLED"
            ),
            "agent_thread_insights_llm_synthesis_enabled": os.environ.get(
                "SCIENCE_GRAPHRAG_AGENT_THREAD_INSIGHTS_LLM_SYNTHESIS_ENABLED"
            ),
            "agent_tool_search_strict_deferred_activation_enabled": os.environ.get(
                "SCIENCE_GRAPHRAG_AGENT_TOOL_SEARCH_STRICT_DEFERRED_ACTIVATION_ENABLED"
            ),
        },
    }
    if phoenix_pull_meta:
        review_dict["phoenix_pull"] = phoenix_pull_meta

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(review_dict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    _write_markdown(args.out_md, review_dict)

    compaction_meta: dict[str, Any] | None = None
    merge_target = args.emit_merged_review or args.out_json
    if args.with_compaction_turns > 0:
        comp_json = args.out_json.parent / f"{args.out_json.stem}_compaction_review.json"
        compaction_meta = _run_compaction_turn_review(
            base_url=args.base_url,
            workspace_id=args.workspace_id,
            timeout=args.timeout,
            turns=args.with_compaction_turns,
            require_after=args.require_compaction_after,
            out_json=comp_json,
            emit_merged_into=merge_target,
        )
        if merge_target.exists():
            try:
                merged = json.loads(merge_target.read_text(encoding="utf-8"))
                merged["compaction_turn_review"] = compaction_meta
                merge_target.write_text(
                    json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                )
                review_dict = merged
                _write_markdown(args.out_md, review_dict)
            except (OSError, json.JSONDecodeError):
                review_dict["compaction_turn_review"] = compaction_meta
                args.out_json.write_text(
                    json.dumps(review_dict, ensure_ascii=False, indent=2) + "\n"
                )
                _write_markdown(args.out_md, review_dict)

    if report_json_path:
        try:
            report_json_path.unlink(missing_ok=True)
        except OSError:
            pass

    print(f"[trace-review] json: {args.out_json}")
    print(f"[trace-review] md:   {args.out_md}")
    print(f"[trace-review] verdict: {review_dict['verdict']['status']}")
    status = str(review_dict["verdict"]["status"])
    return 0 if status != "fail" else 1


if __name__ == "__main__":
    raise SystemExit(main())
