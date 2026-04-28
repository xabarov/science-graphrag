#!/usr/bin/env python3
"""E2E audit: OD workspace agent scenarios + Postgres + Phoenix trace audit.

Loads repo ``.env`` (override=True) like other ``live_check`` scripts. Uses:

- ``SCIENCE_GRAPHRAG_*`` / Neo4j to resolve workspace by name substring
- ``AGENT_LIVE_BASE``, ``AGENT_LIVE_AUTHORIZATION``, ``AGENT_LIVE_ADMIN_KEY``, timeouts
- ``SCIENCE_GRAPHRAG_CHAT_LLM_MODEL`` (via Settings) for reporting
- ``PHOENIX_UI_BASE_URL`` / ``PHOENIX_PROJECT_NAME`` for REST span fetch
  (``eval.chat_agent.phoenix_export``)
- ``AGENT_E2E_PHOENIX_SPAN_CAP`` (optional): max span names stored per case when ``--trace-audit``
  (default ``400``)

**Suites:** ``default`` (3 light), ``heavy`` (3 multi-tool), ``full`` (6 = default + heavy) for
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
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import create_engine, text

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent.parent


def _ensure_paths() -> None:
    if str(_SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPT_DIR))
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))


def _extra_headers() -> dict[str, str]:
    out: dict[str, str] = {}
    auth = (os.environ.get("AGENT_LIVE_AUTHORIZATION") or "").strip()
    if auth:
        out["Authorization"] = auth
    admin = (os.environ.get("AGENT_LIVE_ADMIN_KEY") or "").strip()
    if admin:
        out["X-Admin-Key"] = admin
    return out


def _tool_steps(trace: list[dict[str, Any]]) -> tuple[list[str], int]:
    names: list[str] = []
    for row in trace:
        if not isinstance(row, dict):
            continue
        t = row.get("tool")
        if t:
            names.append(str(t))
    non_session = [n for n in names if n != "session_init"]
    return names, len(non_session)


def _extract_span_names(payload: Any) -> list[str]:
    names: list[str] = []

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            n = obj.get("name")
            if isinstance(n, str) and n.strip():
                names.append(n.strip())
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)

    walk(payload)
    return names


def _question_suite(suite: str) -> list[tuple[str, str]]:
    s = (suite or "default").strip().lower()
    if s == "heavy":
        return HEAVY_QUESTIONS
    if s == "full":
        return list(DEFAULT_QUESTIONS) + list(HEAVY_QUESTIONS)
    return DEFAULT_QUESTIONS


# pylint: disable-next=too-many-locals
def _markdown_report(
    report: dict[str, Any],
    *,
    overall_ok: bool,
) -> str:
    """Human-readable summary for operators (failures, Phoenix, sequence hints)."""

    ws = report.get("workspace") or {}
    lines = [
        "# Agent OD workspace E2E audit",
        "",
        f"- **Suite:** `{report.get('suite')}`",
        f"- **Workspace:** `{ws.get('name')}` (`{ws.get('id')}`), works≈{ws.get('work_count')}",
        f"- **Overall:** {'**PASS**' if overall_ok else '**FAIL**'}",
        "",
        "## Cases",
        "",
        "| case_id | ok | steps | final_answer | answer_len | phoenix | tool_sequence | notes |",
        "|---------|----|-------|--------------|------------|---------|---------------|-------|",
    ]
    for c in report.get("cases") or []:
        cid = str(c.get("case_id") or "")
        steps = c.get("tool_steps_non_session")
        fa = bool(c.get("final_answer_reached"))
        alen = c.get("answer_len")
        ph = c.get("phoenix") or {}
        ph_ok = ph.get("ok") if isinstance(ph, dict) else None
        ok_row = (
            c.get("http_ok")
            and c.get("final_answer_reached")
            and int(c.get("answer_len") or 0) >= 40
        )
        notes = "; ".join(str(x) for x in (c.get("notes") or [])[:4])
        if c.get("error"):
            notes = (notes + "; " if notes else "") + str(c.get("error"))[:120]
        seq = " → ".join(str(x) for x in (c.get("tool_names") or [])[:18])
        if len(c.get("tool_names") or []) > 18:
            seq += " → …"
        lines.append(
            f"| {cid} | {ok_row} | {steps} | {fa} | {alen} | {ph_ok} | {seq} | {notes} |",
        )
    lines.extend(["", "## Trace / Phoenix hints (per case)", ""])
    for c in report.get("cases") or []:
        cid = str(c.get("case_id") or "")
        ta = c.get("trace_audit")
        if not isinstance(ta, dict):
            lines.append(f"### `{cid}`\n\n_(no --trace-audit)_\n")
            continue
        issues = ta.get("heuristic_issues") or []
        psa = ta.get("phoenix_structure_audit")
        lines.append(f"### `{cid}`\n")
        lines.append(f"- **Tool issues:** {issues or '—'}\n")
        if isinstance(psa, dict):
            lines.append(
                "- **Phoenix structure:** issues="
                f"{psa.get('issues') or '—'}; "
                f"llm_turns={psa.get('llm_agent_react_turn_hits')}, "
                f"tool_spans={psa.get('tool_dot_span_hits')}, "
                f"sample_size={psa.get('span_sample_size')}\n"
            )
            sh = psa.get("sequence_hints") or []
            if sh:
                lines.append("- **Sequence / prompt hints:**\n")
                for h in sh:
                    lines.append(f"  - {h}\n")
        lines.append("")
    lines.extend(
        [
            "## JSON",
            "",
            "Machine JSON is on stdout for that run; use --write-report for JSONL artifacts.",
            "",
        ]
    )
    return "\n".join(lines)


def _postgres_workspace_ingest_counts(database_url: str, workspace_id: str) -> dict[str, Any]:
    engine = create_engine(database_url, pool_pre_ping=True)
    out: dict[str, Any] = {"ingest_jobs_total": None, "ingest_jobs_completed": None, "error": None}
    try:
        with engine.connect() as conn:
            r = conn.execute(
                text(
                    "SELECT COUNT(*) FROM ingest_jobs WHERE workspace_id = :wid",
                ),
                {"wid": workspace_id},
            )
            out["ingest_jobs_total"] = int(r.scalar() or 0)
            r2 = conn.execute(
                text(
                    "SELECT COUNT(*) FROM ingest_jobs WHERE workspace_id = :wid AND status = :st",
                ),
                {"wid": workspace_id, "st": "completed"},
            )
            out["ingest_jobs_completed"] = int(r2.scalar() or 0)
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        engine.dispose()
    return out


def _pick_workspace(
    workspaces: list[dict[str, Any]],
    *,
    needle: str,
    min_works: int,
) -> dict[str, Any] | None:
    n = (needle or "").strip().lower()
    candidates = [
        w
        for w in workspaces
        if n in (w.get("name") or "").lower() and len(w.get("work_ids") or []) >= min_works
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda w: len(w.get("work_ids") or []))


def _run_single_query(  # pylint: disable=too-many-arguments,too-many-locals
    client: httpx.Client,
    *,
    url: str,
    workspace_id: str,
    case_id: str,
    question: str,
    skip_phoenix: bool,
    verbose: bool,
    trace_audit: bool,
    phoenix_span_cap: int,
    phoenix_ui_trace_url: Callable[..., str],
    try_fetch_phoenix_spans: Callable[..., dict[str, Any]],
) -> tuple[dict[str, Any], bool]:
    """Return (case_report, case_ok_for_aggregate)."""
    _ensure_paths()
    from science_graphrag.agent.agent_trace_audit import (  # pylint: disable=import-outside-toplevel
        cypher_query_error_count,
        edge_search_zero_row_max_streak,
        paper_profile_max_consecutive_same_work_id,
    )

    case_report: dict[str, Any] = {
        "case_id": case_id,
        "question": question,
        "http_ok": False,
        "answer_len": 0,
        "final_answer_reached": False,
        "tool_names": [],
        "tool_steps_non_session": 0,
        "phoenix_trace_id": None,
        "phoenix": None,
        "notes": [],
    }
    ok = True
    try:
        r = client.post(
            url,
            json={"question": question, "workspace_id": workspace_id},
            headers={"Accept": "application/json", **_extra_headers()},
        )
        r.raise_for_status()
        data = r.json()
    except Exception as exc:  # noqa: BLE001
        case_report["error"] = str(exc)
        return case_report, False

    case_report["http_ok"] = True
    trace = data.get("tool_trace") or []
    if not isinstance(trace, list):
        trace = []
    names, n_steps = _tool_steps(trace)
    case_report["tool_names"] = names
    case_report["tool_steps_non_session"] = n_steps
    case_report["edge_search_zero_row_max_streak"] = edge_search_zero_row_max_streak(trace)
    case_report["paper_profile_max_consecutive_same_work_id"] = (
        paper_profile_max_consecutive_same_work_id(trace)
    )
    case_report["cypher_query_error_count"] = cypher_query_error_count(trace)
    case_report["duration_ms"] = data.get("duration_ms")
    case_report["warnings"] = data.get("warnings") or []
    ans = str(data.get("answer") or "").strip()
    case_report["answer_len"] = len(ans)
    case_report["answer_class"] = data.get("answer_class")
    case_report["citations_count"] = len(data.get("citations") or [])
    tid = (data.get("phoenix_trace_id") or "").strip() or None
    case_report["phoenix_trace_id"] = tid
    if tid:
        case_report["phoenix_ui_url"] = phoenix_ui_trace_url(trace_id=tid)

    if names and names[-1] == "final_answer":
        case_report["final_answer_reached"] = True
    else:
        case_report["notes"].append("last_tool_not_final_answer")
        ok = False

    if len(ans) < 40:
        case_report["notes"].append("very_short_answer_under_40_chars")
        ok = False

    if not skip_phoenix and tid:
        snap = try_fetch_phoenix_spans(tid, timeout_s=20.0)
        span_names = _extract_span_names(snap.get("payload"))
        phx: dict[str, Any] = {
            "ok": snap.get("ok"),
            "payload_kind": snap.get("payload_kind"),
            "error": snap.get("error"),
            "span_name_count": len(span_names),
            "span_names_sample": span_names[:40],
        }
        if trace_audit:
            cap = max(50, min(int(phoenix_span_cap), 2000))
            phx["span_names_full_cap200"] = span_names[:cap]
        case_report["phoenix"] = phx
        if not snap.get("ok"):
            case_report["notes"].append("phoenix_fetch_failed")
    elif not tid:
        case_report["notes"].append("missing_phoenix_trace_id")

    if verbose:
        case_report["tool_trace_verbose"] = trace

    return case_report, ok


HEAVY_QUESTIONS: list[tuple[str, str]] = [
    (
        "multi_compare_bibliography",
        (
            "Compare two detector families in this workspace: (A) works whose titles mention "
            "'YOLO' and (B) works whose titles mention 'Faster R-CNN' or 'Mask R-CNN'. "
            "Use find_works with workspace_id for each query. Pick one best match per family, "
            "call paper_profile for each work_id, then format_bibliography_gost for exactly "
            "those two work_ids. Write a short contrastive paragraph (speed vs accuracy themes) "
            "grounded only in tool outputs. Finish with final_answer and citations for both works."
        ),
    ),
    (
        "graph_ego_methods",
        (
            "Pick one object-detection paper in this workspace (use workspace_inspect mode=papers "
            "or find_works to get a concrete work_id). Using only read-only graph tools "
            "(edge_search and/or cypher_query with LIMIT 40), list Method or Dataset nodes "
            "linked to that work within 2 hops. Summarize linkage strictly from returned rows—"
            "do not invent node ids. If the graph is empty for that work, say so explicitly. "
            "Finish with final_answer."
        ),
    ),
    (
        "multi_evidence_speed_accuracy",
        (
            "What trade-offs between speed and accuracy for real-time object detection does this "
            "workspace support with evidence? Use at least two distinct retrieval paths among "
            "idea_search, paper_quote_search, and workspace_inspect (blurb or papers). "
            "Cite at least two different work_ids from tool outputs. If evidence is thin, "
            "state coverage gaps explicitly. Finish with final_answer."
        ),
    ),
]


DEFAULT_QUESTIONS: list[tuple[str, str]] = [
    (
        "catalog_resolution",
        (
            "In this workspace, find works whose titles mention 'Faster R-CNN' or 'Mask R-CNN' "
            "(use find_works with the workspace_id if titles are unknown). Pick one clear match "
            "and report year and venue using paper_profile. End with final_answer and citations."
        ),
    ),
    (
        "workspace_stats",
        (
            "How many works are in this workspace? Use workspace_inspect with mode=stats (and "
            "other tools only if needed). Summarize any claim-related or citation-related counts "
            "the tools return—do not invent numbers. Finish with final_answer."
        ),
    ),
    (
        "grounded_quote",
        (
            "Search this workspace for evidence about 'anchor-free' or 'anchor free' object "
            "detection (paper_quote_search and/or idea_search). Quote one short snippet with "
            "work_id in citations. Use final_answer when done."
        ),
    ),
]


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
        "--dry-run",
        action="store_true",
        help="Resolve workspace + Postgres ingest counts only (no HTTP / no LLM)",
    )
    parser.add_argument("--verbose", action="store_true", help="Print full tool_trace per case")
    parser.add_argument(
        "--suite",
        choices=("default", "heavy", "full"),
        default="default",
        help="Question pack: default (3), heavy (3), full (6 = default+heavy)",
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
        "--markdown-report",
        type=Path,
        default=None,
        help="Write human-readable Markdown summary (failures, trace_audit, Phoenix hints)",
    )
    args = parser.parse_args()

    from dotenv_util import (
        load_dotenv_or_warn,  # pylint: disable=import-outside-toplevel,import-error
    )

    load_dotenv_or_warn(args.env_file)

    from eval.chat_agent.phoenix_export import (  # pylint: disable=import-outside-toplevel
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
            )
            if args.trace_audit:
                case_report["trace_audit"] = build_tool_trace_audit(case_report)
            if not case_ok:
                overall_ok = False
            report["cases"].append(case_report)

    print(json.dumps(report, indent=2, ensure_ascii=False))

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
