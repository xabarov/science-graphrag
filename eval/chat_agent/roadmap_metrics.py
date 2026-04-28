"""Scoring + derived diagnostics for roadmap chat-agent cases."""

from __future__ import annotations

from collections import Counter
from typing import Any

_GRAPH_TOOL_NAMES = frozenset({"cypher_query", "edge_search"})


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
    cites = report.get("citations")
    if cites is None:
        cites = (report.get("final_output") or {}).get("citations")
    cites_list = cites if isinstance(cites, list) else []
    out = report.get("final_output") or report
    bib = out.get("bibliography") if isinstance(out.get("bibliography"), dict) else {}
    filtered = bib.get("filtered_work_ids") if isinstance(bib, dict) else None
    filtered_n = len(filtered) if isinstance(filtered, list) else 0
    entries = bib.get("entries") if isinstance(bib, dict) else None
    bib_entry_n = len(entries) if isinstance(entries, list) else 0
    budget_exhausted = any(
        str((s.get("args_summary") or {}).get("reason") or "").strip().lower() == "budget_exhausted"
        for s in trace
        if isinstance(s, dict)
    )
    tool_trace_error_count = sum(
        1 for s in trace if isinstance(s, dict) and s.get("error") not in (None, "", False, 0)
    )
    obs = report.get("observability") if isinstance(report.get("observability"), dict) else {}
    obs_reliable = bool(obs.get("observability_match_reliable"))
    obs_passed = bool(obs.get("observability_passed", True))
    return {
        "tool_call_count": len(names),
        "non_final_tool_call_count": len(non_final),
        "first_non_final_tool": non_final[0] if non_final else None,
        "unique_tools": sorted(set(names)),
        "repeated_non_final_tools": repeated,
        "citation_count": len(cites_list),
        "citations_missing_work_id": sum(
            1 for c in cites_list if isinstance(c, dict) and not str(c.get("work_id") or "").strip()
        ),
        "answer_class": out.get("answer_class"),
        "phoenix_trace_id_present": bool(out.get("phoenix_trace_id")),
        "warnings_count": len(out.get("warnings") or []),
        "has_bibliography_block": bool(out.get("bibliography")),
        "bibliography_entry_count": bib_entry_n,
        "bibliography_filtered_work_ids_count": filtered_n,
        "has_inventory_block": bool(out.get("inventory")),
        "has_quote_candidates": bool(out.get("quote_candidates")),
        "has_relation_trace": bool(out.get("relation_trace")),
        "has_idea_suggestions": bool(out.get("idea_suggestions")),
        "budget_exhausted_in_trace": budget_exhausted,
        "tool_trace_error_count": tool_trace_error_count,
        "observability_passed": obs_passed,
        "observability_match_reliable": obs_reliable,
        "phoenix_payload_valid": bool(obs.get("phoenix_payload_valid")),
        "phoenix_payload_kind": obs.get("phoenix_payload_kind"),
        "missing_tool_spans": list(obs.get("missing_tool_spans") or []),
        "missing_retriever_spans": list(obs.get("missing_retriever_spans") or []),
        "expected_span_names": list(obs.get("expected_span_names") or []),
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
    if str(gold.get("eval_tier") or "").lower() == "strict" and "strict_answer_class" not in expect:
        strict_cls = True
    allowed = expect.get("answer_classes_allowed") or []
    if allowed:
        ac = str((report.get("final_output") or report).get("answer_class") or "")
        if ac not in allowed:
            msg = f"answer_class:{ac}_not_in_{allowed}"
            if strict_cls:
                reasons.append(msg)
            else:
                reasons.append(f"soft:{msg}")

    if expect.get("require_graph_tool"):
        if not (_GRAPH_TOOL_NAMES & set(names)):
            reasons.append("require_graph_tool:missing_graph_specialist_tool")

    final_out = report.get("final_output") or report
    if expect.get("require_typed_bibliography"):
        ob = (
            final_out.get("bibliography") if isinstance(final_out.get("bibliography"), dict) else {}
        )
        bib_ok = (
            bool(ob.get("entries"))
            or str(ob.get("format") or "").strip().lower() == "gost"
            or (isinstance(ob.get("lines"), list) and bool(ob.get("lines")))
        )
        if not bib_ok:
            reasons.append("require_typed_bibliography:missing_or_empty")

    if expect.get("require_relation_trace"):
        rt = final_out.get("relation_trace")
        if not isinstance(rt, dict) or not rt:
            reasons.append("require_relation_trace:missing_or_empty")

    max_err = expect.get("max_tool_trace_errors")
    if isinstance(max_err, int) and max_err >= 0:
        err_n = sum(
            1 for s in trace if isinstance(s, dict) and s.get("error") not in (None, "", False, 0)
        )
        if err_n > max_err:
            reasons.append(f"max_tool_trace_errors:want_at_most_{max_err}_got_{err_n}")

    if expect.get("require_observability_match"):
        diag = derive_diagnostics(report)
        if bool(diag.get("observability_match_reliable")) and not bool(
            diag.get("observability_passed", True)
        ):
            reasons.append(
                "observability_match:phoenix_snapshot_missing_expected_tool_or_retriever_spans"
            )

    hard = [r for r in reasons if not str(r).startswith("soft:")]
    passed = len(hard) == 0
    return {
        "passed": passed,
        "reasons": reasons or ["ok"],
        "diagnostics": derive_diagnostics(report),
    }
