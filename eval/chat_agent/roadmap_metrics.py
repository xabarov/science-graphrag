"""Scoring + derived diagnostics for roadmap chat-agent cases."""

from __future__ import annotations

from collections import Counter
from typing import Any


def _tool_names(trace: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for step in trace:
        name = str(step.get("tool") or "")
        if name:
            out.append(name)
    return out


def derive_diagnostics(report: dict[str, Any]) -> dict[str, Any]:
    """Lightweight metrics from a single-case ``report`` dict."""

    trace = list(report.get("tool_trace") or [])
    names = _tool_names(trace)
    non_final = [n for n in names if n != "final_answer"]
    counts = Counter(names)
    repeated = [n for n, c in counts.items() if c > 1 and n != "final_answer"]
    cites = report.get("citations") or []
    out = report.get("final_output") or report
    return {
        "tool_call_count": len(names),
        "non_final_tool_call_count": len(non_final),
        "unique_tools": sorted(set(names)),
        "repeated_non_final_tools": repeated,
        "citation_count": len(cites) if isinstance(cites, list) else 0,
        "answer_class": out.get("answer_class"),
        "phoenix_trace_id_present": bool(out.get("phoenix_trace_id")),
        "warnings_count": len(out.get("warnings") or []),
        "has_bibliography_block": bool(out.get("bibliography")),
        "has_inventory_block": bool(out.get("inventory")),
        "has_quote_candidates": bool(out.get("quote_candidates")),
        "has_relation_trace": bool(out.get("relation_trace")),
        "has_idea_suggestions": bool(out.get("idea_suggestions")),
    }


def score_roadmap_case(report: dict[str, Any], gold: dict[str, Any]) -> dict[str, Any]:
    """Return ``metrics`` with ``passed`` and human-readable ``reasons``."""

    reasons: list[str] = []
    expect = gold.get("expect") if isinstance(gold.get("expect"), dict) else {}
    trace = list(report.get("tool_trace") or [])
    names = _tool_names(trace)
    non_final = [n for n in names if n != "final_answer"]

    if report.get("error"):
        return {
            "passed": False,
            "reasons": [f"runtime_error:{report.get('error')}"],
            "diagnostics": {},
        }

    if expect.get("require_phoenix_trace_id"):
        tid = (report.get("final_output") or report).get("phoenix_trace_id")
        if not tid:
            reasons.append("missing_phoenix_trace_id")

    if expect.get("require_tool_trace") and not trace:
        reasons.append("empty_tool_trace")

    min_calls = int(expect.get("min_non_final_tool_calls") or 0)
    if min_calls and len(non_final) < min_calls:
        reasons.append(f"min_non_final_tool_calls:want_at_least_{min_calls}_got_{len(non_final)}")

    any_of = expect.get("tools_any_of") or []
    if any_of:
        hit = [t for t in any_of if t in names]
        if not hit:
            reasons.append(f"tools_any_of:none_of_{any_of}")

    none_of = expect.get("tools_none_of") or []
    if none_of:
        bad = [t for t in none_of if t in names]
        if bad:
            reasons.append(f"tools_none_of:forbidden_present_{bad}")

    strict_cls = bool(expect.get("strict_answer_class"))
    allowed = expect.get("answer_classes_allowed") or []
    if allowed:
        ac = str((report.get("final_output") or report).get("answer_class") or "")
        if ac not in allowed:
            msg = f"answer_class:{ac}_not_in_{allowed}"
            if strict_cls:
                reasons.append(msg)
            else:
                reasons.append(f"soft:{msg}")

    hard = [r for r in reasons if not str(r).startswith("soft:")]
    passed = len(hard) == 0
    return {
        "passed": passed,
        "reasons": reasons or ["ok"],
        "diagnostics": derive_diagnostics(report),
    }
