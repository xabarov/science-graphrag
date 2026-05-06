from __future__ import annotations

import json
from typing import Any


def _tool_sequence_match(expected: list[dict[str, Any]], actual: list[dict[str, Any]]) -> float:
    if not expected:
        return 1.0
    matched = 0
    for idx, exp in enumerate(expected):
        if idx >= len(actual):
            break
        if str(actual[idx].get("tool")) == str(exp.get("tool")) and _args_match_satisfied(
            exp, actual[idx]
        ):
            matched += 1
    return matched / len(expected)


def _execution_only_trace(trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop supervisor routing pseudo-steps (not real tool executions)."""
    return [t for t in trace if str(t.get("tool") or "") != "route_to_specialist"]


def _args_match_satisfied(expected_step: dict[str, Any], actual_step: dict[str, Any]) -> bool:
    """Gold ``args_match`` (live tier / Phase 6) against summarized tool args."""

    am = expected_step.get("args_match")
    if not isinstance(am, dict):
        return True
    blob = json.dumps(actual_step.get("args_summary") or {}, ensure_ascii=False).lower()
    for tok in am.get("query_contains_all") or []:
        if str(tok).lower() not in blob:
            return False
    any_list = am.get("query_contains_any")
    if any_list and not any(str(t).lower() in blob for t in any_list):
        return False
    return True


def _normalize_expected_tool_sequence(raw: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, str):
            out.append({"tool": item})
        elif isinstance(item, dict):
            name = item.get("tool") if item.get("tool") is not None else item.get("tool_name")
            merged = dict(item)
            merged["tool"] = str(name or "")
            out.append(merged)
    return out


def _tool_subsequence_match(expected: list[dict[str, Any]], actual: list[dict[str, Any]]) -> float:
    """Share of expected tools that appear in order as a subsequence of ``actual``."""
    if not expected:
        return 1.0
    aidx = 0
    matched = 0
    for exp in expected:
        target = str(exp.get("tool") or "")
        if not target:
            matched += 1
            continue
        found = False
        while aidx < len(actual):
            act = actual[aidx]
            aidx += 1
            if str(act.get("tool") or "") != target:
                continue
            if not _args_match_satisfied(exp, act):
                continue
            matched += 1
            found = True
            break
        if not found:
            break
    return matched / len(expected)


def _specialist_sequence_match(expected: list[str], actual: list[str]) -> float:
    if not expected:
        return 1.0
    overlap = len(set(expected) & set(actual))
    return overlap / max(len(expected), 1)


def score_agent_case(report: dict[str, Any], gold: dict[str, Any]) -> dict[str, Any]:
    trace = report.get("tool_trace") or []
    exec_trace = _execution_only_trace(trace)
    raw_expected = gold.get("expected_tool_sequence") or []
    expected = _normalize_expected_tool_sequence(raw_expected)
    match_mode = str(gold.get("tool_sequence_match_mode") or "subsequence").lower()
    if match_mode == "prefix":
        corr = _tool_sequence_match(expected, exec_trace)
    else:
        corr = _tool_subsequence_match(expected, exec_trace)
    max_calls = int(gold.get("max_calls") or 8)
    budget_ok = len(exec_trace) <= max_calls
    cypher_safety = all(
        "error" not in t or "forbidden_token" not in str(t.get("error") or "") for t in trace
    )
    citations = report.get("citations") or []
    traced_work_ids = {
        str(item.get("work_id"))
        for t in exec_trace
        for item in (t.get("args_summary", {}).get("items") or [])
        if isinstance(item, dict) and item.get("work_id")
    }
    grounded = True
    if citations:
        grounded = any(
            str(c.get("work_id")) in traced_work_ids or str(c.get("work_id")) for c in citations
        )
    passed = bool(
        corr >= float(gold.get("min_tool_call_correctness") or 0.7) and budget_ok and cypher_safety
    )
    scores = {
        "tool_call_correctness": round(corr, 4),
        "tool_budget_ok": budget_ok,
        "cypher_safety": 1.0 if cypher_safety else 0.0,
        "answer_grounded": 1.0 if grounded else 0.0,
        "passed": passed,
    }
    expected_specialists = gold.get("expected_specialist_sequence")
    if isinstance(expected_specialists, list):
        actual_specialists = [
            str(entry.get("to"))
            for entry in (report.get("routing_log") or [])
            if entry.get("to") not in (None, "supervisor")
        ]
        specialist_match = _specialist_sequence_match(
            [str(item) for item in expected_specialists],
            actual_specialists,
        )
        scores["specialist_sequence_match"] = round(specialist_match, 4)
        min_match = float(gold.get("min_specialist_sequence_match") or 0.5)
        scores["passed"] = bool(scores["passed"] and specialist_match >= min_match)
    return scores
