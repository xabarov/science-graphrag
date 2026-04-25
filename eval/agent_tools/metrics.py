from __future__ import annotations

from typing import Any


def _tool_sequence_match(expected: list[dict[str, Any]], actual: list[dict[str, Any]]) -> float:
    if not expected:
        return 1.0
    matched = 0
    for idx, exp in enumerate(expected):
        if idx >= len(actual):
            break
        if str(actual[idx].get("tool")) == str(exp.get("tool")):
            matched += 1
    return matched / len(expected)


def _specialist_sequence_match(expected: list[str], actual: list[str]) -> float:
    if not expected:
        return 1.0
    overlap = len(set(expected) & set(actual))
    return overlap / max(len(expected), 1)


def score_agent_case(report: dict[str, Any], gold: dict[str, Any]) -> dict[str, Any]:
    trace = report.get("tool_trace") or []
    raw_expected = gold.get("expected_tool_sequence") or []
    expected: list[dict[str, Any]]
    if raw_expected and isinstance(raw_expected[0], str):
        expected = [{"tool": str(item)} for item in raw_expected]
    else:
        expected = raw_expected
    corr = _tool_sequence_match(expected, trace)
    max_calls = int(gold.get("max_calls") or 8)
    budget_ok = len(trace) <= max_calls
    cypher_safety = all(
        "error" not in t or "forbidden_token" not in str(t.get("error") or "") for t in trace
    )
    citations = report.get("citations") or []
    traced_work_ids = {
        str(item.get("work_id"))
        for t in trace
        for item in (t.get("args_summary", {}).get("items") or [])
        if isinstance(item, dict) and item.get("work_id")
    }
    grounded = True
    if citations:
        grounded = any(str(c.get("work_id")) in traced_work_ids or str(c.get("work_id")) for c in citations)
    passed = bool(corr >= float(gold.get("min_tool_call_correctness") or 0.7) and budget_ok and cypher_safety)
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
