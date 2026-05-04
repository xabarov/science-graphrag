#!/usr/bin/env python3
"""Read-only diagnostics for agent_tools_mini live JSON vs gold expected_tool_sequence.

Prints a markdown table to stdout. Does not call LLMs or databases.

Example::

  .venv/bin/python scripts/diag_agent_tools_mini.py \\
    --live-json eval/results/habr-window-2026-06-agent-tools-mini-band-1.35-live.json \\
    --fixtures-root tests/fixtures/benchmarks/agent_tools_v1
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_COORDINATOR_TOOLS = frozenset({"coordinator_gate"})


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _gold_path(fixtures_root: Path, case_id: str) -> Path:
    return fixtures_root / case_id / "gold.json"


def _expected_first_tool(gold: dict[str, Any]) -> str:
    seq = gold.get("expected_tool_sequence") or []
    if not seq or not isinstance(seq[0], dict):
        return ""
    return str(seq[0].get("tool") or "")


def _observed_tools(trace: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for step in trace:
        if not isinstance(step, dict):
            continue
        name = str(step.get("tool") or "")
        if name in _COORDINATOR_TOOLS:
            continue
        out.append(name)
    return out


def _trace_errors(trace: list[dict[str, Any]]) -> list[str | None]:
    errs: list[str | None] = []
    for step in trace:
        if not isinstance(step, dict):
            continue
        errs.append(step.get("error"))  # type: ignore[assignment]
    return errs


def _classify_v2(
    *,
    passed: bool,
    tool_corr: float,
    budget_ok: bool,
    answer_grounded: float,
    duration_ms: int,
    observed: list[str],
    expected_first: str,
    expected_len: int,
    trace_errors: list[str | None],
) -> str:
    if passed:
        return "ok"

    classes: list[str] = []

    if answer_grounded < 1.0 - 1e-9:
        classes.append("answer_ungrounded")

    first = observed[0] if observed else ""
    if expected_first and first and first != expected_first:
        classes.append("wrong_first_tool")

    if (not budget_ok) and tool_corr < 0.7:
        classes.append("over_budget")

    if len(observed) - expected_len >= 2 and tool_corr < 0.5:
        classes.append("extra_tool_loops")

    if (not passed) and all(e is None for e in trace_errors) and duration_ms > 60_000:
        classes.append("slow_no_error")

    if not classes and (not passed) and tool_corr < 0.7:
        classes.append("low_tool_correctness")

    if not classes:
        return "unknown"

    return "mixed" if len(classes) > 1 else classes[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live-json",
        type=Path,
        required=True,
        help="Path to agent_tools_mini live suite JSON.",
    )
    parser.add_argument(
        "--fixtures-root",
        type=Path,
        default=Path("tests/fixtures/benchmarks/agent_tools_v1"),
        help="Root of agent_tools_v1 fixtures.",
    )
    args = parser.parse_args(argv)

    live_path = args.live_json.resolve()
    fixtures_root = args.fixtures_root.resolve()
    if not live_path.is_file():
        print(f"Missing live JSON: {live_path}", file=sys.stderr)
        return 2

    suite = _load_json(live_path)
    cases = suite.get("cases") or []
    if not cases:
        print("No cases in suite JSON", file=sys.stderr)
        return 2

    rows: list[dict[str, Any]] = []
    for c in cases:
        cid = str(c.get("case_id") or "")
        metrics = c.get("metrics") if isinstance(c.get("metrics"), dict) else {}
        passed = bool(metrics.get("passed", False))
        tool_corr = float(metrics.get("tool_call_correctness") or 0.0)
        budget_ok = bool(metrics.get("tool_budget_ok", True))
        answer_grounded = float(metrics.get("answer_grounded") or 1.0)
        duration_ms = int(c.get("duration_ms") or 0)
        trace = c.get("tool_trace") if isinstance(c.get("tool_trace"), list) else []
        observed = _observed_tools(trace)
        errs = _trace_errors(trace)

        gpath = _gold_path(fixtures_root, cid)
        if not gpath.is_file():
            gold: dict[str, Any] = {}
        else:
            gold = _load_json(gpath)

        exp_seq = gold.get("expected_tool_sequence") or []
        expected_len = len(exp_seq) if isinstance(exp_seq, list) else 0
        expected_first = _expected_first_tool(gold)

        failure = _classify_v2(
            passed=passed,
            tool_corr=tool_corr,
            budget_ok=budget_ok,
            answer_grounded=answer_grounded,
            duration_ms=duration_ms,
            observed=observed,
            expected_first=expected_first,
            expected_len=expected_len,
            trace_errors=errs,
        )

        rows.append(
            {
                "case_id": cid,
                "passed": passed,
                "tool_correctness": round(tool_corr, 4),
                "budget_ok": budget_ok,
                "answer_grounded": round(answer_grounded, 4),
                "duration_ms": duration_ms,
                "observed_tools": " → ".join(observed) if observed else "(empty)",
                "expected_first": expected_first or "(none)",
                "failure_class": failure,
            }
        )

    print(
        "| case_id | passed | tool_correctness | budget_ok | answer_grounded | duration_ms | expected_first | failure_class | observed_tools |"
    )
    print("|---|---:|---:|---:|---:|---:|---|---|---|")
    for r in rows:
        print(
            f"| `{r['case_id']}` | {str(r['passed']).lower()} | {r['tool_correctness']} | "
            f"{str(r['budget_ok']).lower()} | {r['answer_grounded']} | {r['duration_ms']} | "
            f"`{r['expected_first']}` | `{r['failure_class']}` | {r['observed_tools']} |"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
