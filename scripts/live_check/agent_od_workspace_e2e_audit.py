#!/usr/bin/env python3
"""E2E audit: OD workspace agent scenarios + Postgres + Phoenix trace audit.

Loads repo ``.env`` (override=True) like other ``live_check`` scripts. Uses:

- ``SCIENCE_GRAPHRAG_*`` / Neo4j to resolve workspace by name substring
- ``AGENT_LIVE_BASE``, ``AGENT_LIVE_AUTHORIZATION``, ``AGENT_LIVE_ADMIN_KEY``, timeouts
- ``SCIENCE_GRAPHRAG_CHAT_LLM_MODEL`` (via Settings) for reporting
- ``PHOENIX_UI_BASE_URL`` / ``PHOENIX_PROJECT_NAME`` for REST span fetch
  (``eval.chat_agent.phoenix_export``); span names are **trace-scoped** (no recursive ``name`` walk).
- ``AGENT_E2E_PHOENIX_SPAN_CAP`` (optional): max span names stored per case when ``--trace-audit``
  (default ``400``)

**Suites:** ``default`` (3 light), ``heavy`` (3 multi-tool), ``full`` (6 = default + heavy),
``acceptance`` (full + v3 hardening prompts for live gates) for
post–phases A/B/C regression and Phoenix sequence review.

**Phoenix:** With ``--trace-audit``, each case gets ``trace_audit`` (tool heuristics) plus
``phoenix_structure_audit`` when Phoenix REST returns span names — flags missing LLM/tool spans and
sequence hints (prompt/tool alignment). See ``science_graphrag.agent.agent_trace_audit``.

Usage::

    cd /path/to/science-graphrag
    .venv/bin/python scripts/live_check/agent_od_workspace_e2e_audit.py --verbose
    .venv/bin/python scripts/live_check/agent_od_workspace_e2e_audit.py \\
        --workspace-name-substring "Object Detection" --skip-phoenix
    .venv/bin/python scripts/live_check/agent_od_workspace_e2e_audit.py --suite heavy \\
        --trace-audit --timeout 600
    .venv/bin/python scripts/live_check/agent_od_workspace_e2e_audit.py --suite full \\
        --trace-audit --markdown-report /tmp/agent_od_audit.md

Exit codes:

- ``0`` — all cases HTTP-ok, ``final_answer`` is the last catalog tool in ``tool_trace``, answer
  length ≥ 40 chars (Phoenix fetch failures still fail a case when trace id present and not
  ``--skip-phoenix``).
- ``1`` — at least one case failed the checks above (use for CI / nightly gates).
- ``2`` — workspace resolution failed (no name match / too few works).
- ``3`` — API ``/health`` not HTTP 200.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from agent_od_audit.bootstrap import REPO_ROOT as _REPO_ROOT
from agent_od_audit.bootstrap import ensure_paths as _ensure_paths
from agent_od_audit.query_runner import run_single_query as _run_single_query
from agent_od_audit.report_markdown import markdown_report as _markdown_report
from agent_od_audit.retry_policy import (
    case_passes_acceptance as _case_passes_acceptance,
    should_retry_after_case_failure as _should_retry_after_case_failure,
    should_retry_after_provider_flake as _should_retry_after_provider_flake,
    should_retry_after_transport_flake as _should_retry_after_transport_flake,
)
from agent_od_audit.suites import question_suite as _question_suite
from agent_od_audit.workspace_ingest import (
    pick_workspace as _pick_workspace,
    postgres_workspace_ingest_counts as _postgres_workspace_ingest_counts,
)


def main() -> int:  # pylint: disable=too-many-locals,too-many-statements
    """CLI entry."""
    _ensure_paths()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        type=Path,
        default=_REPO_ROOT / ".env",
        help="Dotenv path (default: repo .env)",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("AGENT_LIVE_BASE", "http://127.0.0.1:8000"),
        help="API base (env AGENT_LIVE_BASE)",
    )
    parser.add_argument(
        "--workspace-name-substring",
        default=os.environ.get("AGENT_OD_WORKSPACE_NAME", "Object Detection"),
        help="Pick Neo4j workspace whose name contains this substring (case-insensitive)",
    )
    parser.add_argument(
        "--min-works",
        type=int,
        default=25,
        help="Fail resolve if fewer works linked to workspace (default 25)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.environ.get("AGENT_LIVE_TIMEOUT_SEC", "300")),
        help="HTTP read timeout seconds",
    )
    parser.add_argument("--skip-phoenix", action="store_true", help="Do not call Phoenix REST")
    parser.add_argument(
        "--skip-postgres",
        action="store_true",
        help="Backward-compatible no-op flag (kept for trace-review CLI compatibility).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve workspace + Postgres ingest counts only (no HTTP / no LLM)",
    )
    parser.add_argument("--verbose", action="store_true", help="Print full tool_trace per case")
    parser.add_argument(
        "--suite",
        choices=("default", "heavy", "full", "acceptance"),
        default="default",
        help="Question pack: default (3), heavy (3), full (6), acceptance (full + v3 prompts)",
    )
    parser.add_argument(
        "--trace-audit",
        action="store_true",
        help="Add per-case trace_audit heuristics (tool fan-out, Phoenix sample hits)",
    )
    parser.add_argument(
        "--write-report",
        type=Path,
        default=None,
        help="Append one JSON line per full run (suite summary + cases) for CI artifacts",
    )
    parser.add_argument(
        "--write-report-json",
        type=Path,
        default=None,
        help="Write full machine JSON report (same structure as stdout) for orchestrators",
    )
    parser.add_argument(
        "--markdown-report",
        type=Path,
        default=None,
        help="Write human-readable Markdown summary (failures, trace_audit, Phoenix hints)",
    )
    args = parser.parse_args()

    from dotenv_util import (  # pylint: disable=import-outside-toplevel,import-error
        load_dotenv_or_warn,
    )
    from dotenv_util import (  # pylint: disable=import-outside-toplevel,import-error
        resolve_live_base_url,
    )

    load_dotenv_or_warn(args.env_file)
    args.base_url = resolve_live_base_url(args.base_url)

    from eval.chat_agent.phoenix_export import (  # pylint: disable=import-outside-toplevel
        extract_span_names_for_trace,
        phoenix_ui_trace_url,
        try_fetch_phoenix_spans,
    )
    from science_graphrag.agent.agent_trace_audit import (  # pylint: disable=import-outside-toplevel
        build_tool_trace_audit,
    )
    from science_graphrag.api.deps import (  # pylint: disable=import-outside-toplevel
        close_store_registry,
        init_store_registry,
    )
    from science_graphrag.config import get_settings  # pylint: disable=import-outside-toplevel

    settings = get_settings()
    stores = init_store_registry(settings)
    try:
        workspaces = stores.neo4j.workspace_list()
    finally:
        close_store_registry()

    needle = (args.workspace_name_substring or "").strip().lower()
    picked = _pick_workspace(workspaces, needle=needle, min_works=args.min_works)
    if picked is None:
        short = [
            {
                "id": w.get("id"),
                "name": w.get("name"),
                "n_works": len(w.get("work_ids") or []),
            }
            for w in workspaces[:30]
        ]
        print(
            json.dumps(
                {
                    "error": "no_workspace_match",
                    "needle": needle,
                    "min_works": args.min_works,
                    "sample_workspaces": short,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 2

    ws = picked
    workspace_id = str(ws["id"])
    ws_name = str(ws.get("name") or "")
    work_count = len(ws.get("work_ids") or [])

    scope = (os.environ.get("PHOENIX_TRACE_SCOPE") or "").strip().lower()
    if scope == "extraction_llm":
        print(
            "note: PHOENIX_TRACE_SCOPE=extraction_llm (agent.* spans still allowed); "
            "if Phoenix is empty, check PHOENIX_COLLECTOR_ENDPOINT on the API container.",
            file=sys.stderr,
        )

    db_audit = _postgres_workspace_ingest_counts(
        settings.database_url,
        workspace_id,
    )

    report: dict[str, Any] = {
        "suite": args.suite,
        "workspace": {"id": workspace_id, "name": ws_name, "work_count": work_count},
        "llm": {"chat_model": settings.chat_llm_model},
        "postgres_ingest_jobs": db_audit,
        "cases": [],
    }

    if args.dry_run:
        report["dry_run"] = True
        report["suite"] = args.suite
        report["planned_questions"] = [
            {"case_id": c, "question": q} for c, q in _question_suite(args.suite)
        ]
        print(json.dumps(report, indent=2, ensure_ascii=False))
        print("\n--- dry-run: no agent calls ---", file=sys.stderr)
        return 0

    base = args.base_url.rstrip("/")
    url = f"{base}/v2/agent/query"
    timeout_cfg = httpx.Timeout(connect=30.0, read=args.timeout, write=120.0, pool=20.0)

    phoenix_span_cap = int(os.environ.get("AGENT_E2E_PHOENIX_SPAN_CAP", "400"))

    overall_ok = True
    with httpx.Client(timeout=timeout_cfg) as client:
        health = client.get(f"{base}/health")
        if health.status_code != 200:
            print(json.dumps({"error": "health_failed", "status": health.status_code}))
            return 3

        for case_id, question in _question_suite(args.suite):
            case_report, case_ok = _run_single_query(
                client,
                url=url,
                workspace_id=workspace_id,
                case_id=case_id,
                question=question,
                skip_phoenix=args.skip_phoenix,
                verbose=args.verbose,
                trace_audit=args.trace_audit,
                phoenix_span_cap=phoenix_span_cap,
                phoenix_ui_trace_url=phoenix_ui_trace_url,
                try_fetch_phoenix_spans=try_fetch_phoenix_spans,
                extract_span_names_for_trace_fn=extract_span_names_for_trace,
            )
            retries = 0
            while (
                retries < 1
                and (not case_ok)
                and (
                    _should_retry_after_case_failure(case_report)
                    or _should_retry_after_transport_flake(case_report)
                    or _should_retry_after_provider_flake(case_report)
                )
            ):
                retries += 1
                if _should_retry_after_transport_flake(case_report):
                    case_report["notes"].append("retry_after_transport_error")
                    time.sleep(2.0)
                elif _should_retry_after_provider_flake(case_report):
                    case_report["notes"].append("retry_after_provider_error_response")
                    time.sleep(2.0)
                else:
                    case_report["notes"].append("retry_after_deadline_exceeded")
                case_report, case_ok = _run_single_query(
                    client,
                    url=url,
                    workspace_id=workspace_id,
                    case_id=case_id,
                    question=question,
                    skip_phoenix=args.skip_phoenix,
                    verbose=args.verbose,
                    trace_audit=args.trace_audit,
                    phoenix_span_cap=phoenix_span_cap,
                    phoenix_ui_trace_url=phoenix_ui_trace_url,
                    try_fetch_phoenix_spans=try_fetch_phoenix_spans,
                    extract_span_names_for_trace_fn=extract_span_names_for_trace,
                )
                case_report["retry_count"] = retries
            if args.trace_audit:
                case_report["trace_audit"] = build_tool_trace_audit(case_report)
            if not case_ok:
                overall_ok = False
            report["cases"].append(case_report)

    report_json_text = json.dumps(report, indent=2, ensure_ascii=False)
    print(report_json_text)

    if args.write_report_json:
        args.write_report_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_report_json.write_text(report_json_text + "\n", encoding="utf-8")
        print(f"wrote full report json: {args.write_report_json}", file=sys.stderr)

    if args.markdown_report:
        args.markdown_report.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_report.write_text(
            _markdown_report(report, overall_ok=overall_ok),
            encoding="utf-8",
        )
        print(f"wrote markdown report: {args.markdown_report}", file=sys.stderr)

    if args.write_report:
        line = {
            "suite": report.get("suite"),
            "workspace_id": (report.get("workspace") or {}).get("id"),
            "overall_ok": overall_ok,
            "cases": [
                {
                    "case_id": c.get("case_id"),
                    "final_answer_reached": c.get("final_answer_reached"),
                    "http_ok": c.get("http_ok"),
                    "answer_len": c.get("answer_len"),
                }
                for c in report.get("cases") or []
            ],
        }
        args.write_report.parent.mkdir(parents=True, exist_ok=True)
        with args.write_report.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(line, ensure_ascii=False) + "\n")

    # Human-readable summary lines
    print("\n--- summary ---", file=sys.stderr)
    for c in report["cases"]:
        cid = c.get("case_id")
        steps = c.get("tool_steps_non_session")
        ok = c.get("http_ok") and c.get("final_answer_reached") and c.get("answer_len", 0) >= 40
        ph = c.get("phoenix") or {}
        ph_ok = ph.get("ok") if isinstance(ph, dict) else None
        print(
            f"{cid}: steps={steps} final_answer={c.get('final_answer_reached')} "
            f"answer_len={c.get('answer_len')} phoenix_ok={ph_ok} ok={ok}",
            file=sys.stderr,
        )

    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
