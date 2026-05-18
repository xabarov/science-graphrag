#!/usr/bin/env python3
"""Expanded live matrix for external research intents (Phase N3)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.live_check.external_web_hot_topics_cv_audit import (  # noqa: E402
    _phoenix_names,
    _tool_flags,
    _tool_names,
    build_audit_diagnostics,
    evaluate_case_verdicts,
    evaluate_next_slice_gates,
    extract_terminal_reason_from_run_metadata,
)

_DEFAULT_FIXTURE = _REPO_ROOT / "eval/fixtures/agent_external_research_matrix.json"
_DEFAULT_BASE = "http://127.0.0.1:18787"
_DEFAULT_WORKSPACE = "ws-pilot-od"

_TOOL_FAMILY_MAP: dict[str, frozenset[str]] = {
    "web": frozenset({"web_search", "web_fetch", "official_web_lookup"}),
    "scholar": frozenset({"semantic_scholar_search", "semantic_scholar_paper"}),
    "pdf": frozenset({"read_external_pdf"}),
    "corpus": frozenset(
        {
            "find_works",
            "paper_profile",
            "idea_search",
            "paper_quote_search",
            "workspace_inspect",
        }
    ),
    "official": frozenset({"official_web_lookup"}),
    "doi": frozenset({"unpaywall_lookup", "doi_resolver", "crossref_works_search"}),
    "arxiv": frozenset({"arxiv_search", "arxiv_fetch"}),
    "final_answer": frozenset({"final_answer"}),
}


def _flags_for_families(tool_names: list[str]) -> dict[str, bool]:
    names = set(tool_names)
    out: dict[str, bool] = {}
    for family, members in _TOOL_FAMILY_MAP.items():
        out[family] = any(m in names for m in members)
    return out


def _family_issues(
    *,
    tool_names: list[str],
    expected: list[str],
    forbidden: list[str],
) -> list[str]:
    flags = _flags_for_families(tool_names)
    issues: list[str] = []
    for fam in expected:
        if not flags.get(fam):
            issues.append(f"missing_family:{fam}")
    for fam in forbidden:
        if flags.get(fam):
            issues.append(f"forbidden_family:{fam}")
    return issues


def load_matrix_cases(
    fixture_path: Path,
    *,
    suite: str | None,
    suites_filter: list[str] | None,
) -> list[dict[str, Any]]:
    """Load cases from JSON fixture, optionally filtered by suite name(s)."""
    raw = json.loads(fixture_path.read_text(encoding="utf-8"))
    suites = raw.get("suites") if isinstance(raw, dict) else {}
    if not isinstance(suites, dict):
        raise ValueError("fixture must contain suites object")
    out: list[dict[str, Any]] = []
    want = set(suites_filter or [])
    for suite_name, rows in suites.items():
        if suite and suite_name != suite:
            continue
        if want and suite_name not in want:
            continue
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            case = dict(row)
            case["suite"] = suite_name
            out.append(case)
    return out


def evaluate_matrix_case(
    *,
    case: dict[str, Any],
    tool_names: list[str],
    answer: str,
    span_names: list[str],  # noqa: ARG001 — reserved for Phoenix-family gates
    base_verdicts: dict[str, Any],
) -> dict[str, Any]:
    """Apply per-case expected/forbidden tool families and answer heuristics."""
    expected = [str(x) for x in (case.get("expected_tool_families") or []) if str(x).strip()]
    forbidden = [str(x) for x in (case.get("forbidden_tool_families") or []) if str(x).strip()]
    family_issues = _family_issues(
        tool_names=tool_names,
        expected=expected,
        forbidden=forbidden,
    )
    answer_lower = str(answer or "").lower()
    for needle in case.get("answer_must_not_contain") or []:
        if str(needle).lower() in answer_lower:
            family_issues.append(f"overclaim:{needle}")
    must_any = [str(x) for x in (case.get("answer_must_contain_any") or []) if str(x).strip()]
    if must_any and not any(str(x).lower() in answer_lower for x in must_any):
        family_issues.append("missing_limitations_language")

    matrix_ok = not family_issues
    all_ok = bool(base_verdicts.get("ok")) and matrix_ok
    issues = list(base_verdicts.get("issues") or []) + family_issues
    return {
        **base_verdicts,
        "ok": all_ok,
        "issues": issues,
        "matrix": {"ok": matrix_ok, "issues": family_issues},
    }


def evaluate_matrix_gates(coverage: dict[str, Any], *, total_cases: int) -> dict[str, Any]:
    """Ratio-based gates for multi-intent matrix (not the 10-case web-hot-topics slice)."""

    total = max(1, int(total_cases))
    thresholds = {
        "runtime_ok_cases": 0.55,
        "tool_trace_ok_cases": 0.50,
        "phoenix_ok_cases": 0.45,
        "matrix_ok_cases": 0.50,
        "with_final_answer": 0.70,
    }
    checks: dict[str, dict[str, Any]] = {}
    cov = coverage if isinstance(coverage, dict) else {}
    for key, ratio in thresholds.items():
        actual = int(cov.get(key, 0) or 0)
        minimum = max(1, int(total * ratio))
        ok = actual >= minimum
        checks[key] = {"ok": ok, "actual": actual, "minimum": minimum, "ratio": ratio}
    generic = int(cov.get("generic_fallback_with_evidence_cases", 0) or 0)
    checks["generic_fallback_with_evidence_cases"] = {
        "ok": generic == 0,
        "actual": generic,
        "maximum": 0,
    }
    return {
        "all_ok": all(bool(v.get("ok")) for v in checks.values()),
        "checks": checks,
    }


def _render_md(report: dict[str, Any]) -> str:
    lines = [
        "# Agent external research matrix",
        "",
        f"- suite: {report.get('suite') or 'all'}",
        f"- cases: {report.get('total_cases')}",
        f"- passed: {report.get('passed_cases')}",
        f"- lane: {report.get('lane_label')}",
        "",
        "## Coverage",
    ]
    cov = report.get("coverage") or {}
    for key in sorted(cov.keys()):
        lines.append(f"- {key}: {cov[key]}")
    gates = report.get("next_slice_gates") or {}
    lines.append("")
    lines.append(f"## Gates all_ok={gates.get('all_ok')}")
    return "\n".join(lines) + "\n"


def main() -> int:
    """Run the expanded external-research matrix against a live agent API."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("AGENT_LIVE_BASE", _DEFAULT_BASE))
    parser.add_argument(
        "--workspace-id", default=os.getenv("AGENT_LIVE_WORKSPACE_ID", _DEFAULT_WORKSPACE)
    )
    parser.add_argument("--fixture", type=Path, default=_DEFAULT_FIXTURE)
    parser.add_argument(
        "--suite",
        default="",
        help="Run one suite key from fixture (default: all suites).",
    )
    parser.add_argument(
        "--suites",
        default="",
        help="Comma-separated suite keys (subset of fixture).",
    )
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--out-json", default="eval/results/agent-external-research-matrix.json")
    parser.add_argument("--out-md", default="eval/results/agent-external-research-matrix.md")
    parser.add_argument("--lane-label", default="matrix")
    args = parser.parse_args()

    suites_filter = [s.strip() for s in str(args.suites).split(",") if s.strip()]
    cases = load_matrix_cases(
        args.fixture,
        suite=str(args.suite).strip() or None,
        suites_filter=suites_filter or None,
    )
    if not cases:
        print("No cases selected", file=sys.stderr)
        return 2

    base = str(args.base_url).rstrip("/")
    rows: list[dict[str, Any]] = []
    with httpx.Client(timeout=float(args.timeout)) as client:
        for idx, case in enumerate(cases, start=1):
            print(f"[{idx}/{len(cases)}] {case.get('suite')}:{case.get('id')} ...", flush=True)
            payload: dict[str, Any] = {"question": case["question"]}
            ws = str(case.get("workspace_id") or args.workspace_id or "").strip()
            if ws:
                payload["workspace_id"] = ws
            if case.get("web_research_enabled") is not None:
                payload["web_research_enabled"] = bool(case["web_research_enabled"])
            started = time.time()
            try:
                resp = client.post(
                    f"{base}/v2/agent/query",
                    json=payload,
                    headers={"Accept": "application/json"},
                )
                status = int(resp.status_code)
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:  # noqa: BLE001
                verdicts = evaluate_matrix_case(
                    case=case,
                    tool_names=[],
                    answer="",
                    span_names=[],
                    base_verdicts=evaluate_case_verdicts(
                        http_status=None,
                        error=f"{type(exc).__name__}: {exc}",
                        answer="",
                        citations=[],
                        tool_flags=_tool_flags([]),
                        span_names=[],
                        require_web_tools=bool(case.get("web_research_enabled", True)),
                    ),
                )
                rows.append(
                    {
                        "suite": case.get("suite"),
                        "id": case.get("id"),
                        "ok": False,
                        "error": str(exc),
                        "verdicts": verdicts,
                        "elapsed_sec": round(time.time() - started, 2),
                    }
                )
                continue

            tool_trace = data.get("tool_trace") if isinstance(data, dict) else []
            tool_trace = tool_trace if isinstance(tool_trace, list) else []
            flags = _tool_flags(tool_trace)
            tool_names = _tool_names(tool_trace)
            answer = str(data.get("answer") or "")
            citations = data.get("citations") if isinstance(data.get("citations"), list) else []
            run_metadata = (
                data.get("run_metadata") if isinstance(data.get("run_metadata"), dict) else {}
            )
            trace_id = str(data.get("phoenix_trace_id") or "").strip()
            phoenix_meta, span_names = _phoenix_names(trace_id, timeout=float(args.timeout))
            require_web = bool(case.get("web_research_enabled", True))
            base_verdicts = evaluate_case_verdicts(
                http_status=status,
                error=None,
                answer=answer,
                citations=[c for c in citations if isinstance(c, dict)],
                tool_flags=flags,
                span_names=span_names,
                require_web_tools=require_web,
            )
            verdicts = evaluate_matrix_case(
                case=case,
                tool_names=tool_names,
                answer=answer,
                span_names=span_names,
                base_verdicts=base_verdicts,
            )
            rows.append(
                {
                    "suite": case.get("suite"),
                    "id": case.get("id"),
                    "topic": case.get("topic"),
                    "ok": bool(verdicts.get("ok")),
                    "http_status": status,
                    "elapsed_sec": round(time.time() - started, 2),
                    "tool_names": tool_names,
                    "tool_flags": flags,
                    "phoenix_trace_id": trace_id,
                    "phoenix": phoenix_meta,
                    "verdicts": verdicts,
                    "terminal_reason": extract_terminal_reason_from_run_metadata(run_metadata),
                    "audit_diagnostics": build_audit_diagnostics(
                        tool_flags=flags,
                        span_names=span_names,
                    ),
                }
            )
            print(f"  -> ok={verdicts.get('ok')} issues={verdicts.get('issues')}", flush=True)

    coverage = {
        "runtime_ok_cases": sum(
            1 for r in rows if ((r.get("verdicts") or {}).get("runtime") or {}).get("ok")
        ),
        "tool_trace_ok_cases": sum(
            1 for r in rows if ((r.get("verdicts") or {}).get("tool_trace") or {}).get("ok")
        ),
        "phoenix_ok_cases": sum(
            1 for r in rows if ((r.get("verdicts") or {}).get("phoenix") or {}).get("ok")
        ),
        "matrix_ok_cases": sum(
            1 for r in rows if ((r.get("verdicts") or {}).get("matrix") or {}).get("ok")
        ),
        "with_final_answer": sum(
            1 for r in rows if (r.get("tool_flags") or {}).get("final_answer")
        ),
        "generic_fallback_with_evidence_cases": 0,
    }
    report = {
        "lane_label": args.lane_label,
        "suite": str(args.suite or "all"),
        "fixture": str(args.fixture),
        "base_url": base,
        "total_cases": len(rows),
        "passed_cases": sum(1 for r in rows if r.get("ok")),
        "coverage": coverage,
        "next_slice_gates": evaluate_matrix_gates(coverage, total_cases=len(rows)),
        "web_hot_topics_gates": evaluate_next_slice_gates(coverage),
        "cases": rows,
    }
    out_json = Path(args.out_json)
    out_md = Path(args.out_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    out_md.write_text(_render_md(report), encoding="utf-8")
    print(f"Wrote {out_json} ({report['passed_cases']}/{report['total_cases']} passed)", flush=True)
    return 0 if report["passed_cases"] == report["total_cases"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
