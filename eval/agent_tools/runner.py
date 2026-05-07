"""CLI + suite runner for Wave R agent tool-use benchmarks."""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter
from typing import Any

import typer

from eval.agent_tools.metrics import score_agent_case
from eval.bench_common import run_single_case_json_outputs, run_suite_cli_flow
from science_graphrag.agent.runtime import build_agent
from science_graphrag.api.deps import init_store_registry
from science_graphrag.config import get_settings


def discover_agent_case_dirs(fixtures_root: Path, *, tier: str = "agent_tools_mini") -> list[Path]:
    manifest = fixtures_root / "case_tiers.json"
    allowed: set[str] | None = None
    if manifest.is_file():
        raw = json.loads(manifest.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and tier in raw:
            allowed = {str(x) for x in raw[tier]}
    out: list[Path] = []
    for child in sorted(fixtures_root.iterdir()):
        if not child.is_dir():
            continue
        if not (child / "question.txt").is_file() or not (child / "gold.json").is_file():
            continue
        if allowed is not None and child.name not in allowed:
            continue
        out.append(child)
    return out


def _tool_name_from_gold_step(item: Any) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return str(item.get("tool") or item.get("tool_name") or "")
    return ""


def _mock_case_report(
    case_id: str, question: str, *, workspace_id: str | None, gold: dict[str, Any]
) -> dict[str, Any]:
    """Deterministic stub trace aligned with gold (BT8/BT9 CI); not ``mock answer`` / ``mock-work``."""

    raw_expected = gold.get("expected_tool_sequence") or []
    trace: list[dict[str, Any]] = []
    step = 1
    for item in raw_expected:
        tool = _tool_name_from_gold_step(item)
        if not tool:
            continue
        if tool == "final_answer":
            args_summary: dict[str, Any] = {"answer_chars": 24}
            row_count = 1
        elif tool in {"cypher_query", "edge_search"}:
            args_summary = {"query": question[:200]}
            row_count = 2
        elif tool == "lsp_tool":
            args_summary = {"operation": "workspace_symbol", "query": "main"}
            row_count = 2
        else:
            args_summary = {"q": question[:80]}
            row_count = 3
        trace.append(
            {
                "step": step,
                "tool": tool,
                "args_summary": args_summary,
                "row_count": row_count,
                "duration_ms": 1,
                "truncated": False,
                "error": None,
            }
        )
        step += 1
    if not trace:
        trace = [
            {
                "step": 1,
                "tool": "idea_search",
                "args_summary": {"q": question[:40]},
                "row_count": 3,
                "duration_ms": 1,
                "truncated": False,
                "error": None,
            }
        ]
        step = 2
        if workspace_id:
            trace.append(
                {
                    "step": step,
                    "tool": "workspace_inspect",
                    "args_summary": {"workspace_id": workspace_id},
                    "row_count": 2,
                    "duration_ms": 1,
                    "truncated": False,
                    "error": None,
                }
            )
            step += 1
        trace.append(
            {
                "step": step,
                "tool": "final_answer",
                "args_summary": {"answer_chars": 12},
                "row_count": 1,
                "duration_ms": 1,
                "truncated": False,
                "error": None,
            }
        )

    routing_log: list[dict[str, Any]] = []
    budget_left = int(gold.get("max_calls") or 8)
    for spec in gold.get("expected_specialist_sequence") or []:
        routing_log.append(
            {"from": "supervisor", "to": str(spec), "budget_left": budget_left},
        )

    answer = f"benchmark_stub_answer:{case_id}"
    citations = [{"work_id": f"benchmark-stub-work:{case_id}"}]
    duration_ms = max(2, len(trace))
    return {
        "case_id": case_id,
        "question": question,
        "answer": answer,
        "citations": citations,
        "tool_trace": trace,
        "routing_log": routing_log,
        "duration_ms": duration_ms,
    }


def run_agent_case(case_dir: Path, *, mock_runtime: bool = False) -> dict[str, Any]:
    question = (case_dir / "question.txt").read_text(encoding="utf-8").strip()
    gold = json.loads((case_dir / "gold.json").read_text(encoding="utf-8"))
    started = perf_counter()
    if mock_runtime:
        report = _mock_case_report(
            case_dir.name,
            question,
            workspace_id=gold.get("workspace_id"),
            gold=gold,
        )
    else:
        settings = get_settings()
        try:
            stores = init_store_registry(settings)
            agent = build_agent(settings=settings, stores=stores)
            out = agent.run(
                question=question,
                workspace_id=(str(gold.get("workspace_id") or "").strip() or None),
                max_tool_calls=int(gold.get("max_calls") or settings.agent_max_tool_calls),
            )
            report = {
                "case_id": case_dir.name,
                "question": question,
                "answer": out.answer,
                "citations": out.citations,
                "tool_trace": list(out.tool_trace),
                "routing_log": list(out.routing_log or []),
                "duration_ms": int((perf_counter() - started) * 1000),
            }
        except Exception as exc:  # noqa: BLE001 — benchmark must emit JSON
            report = {
                "case_id": case_dir.name,
                "question": question,
                "answer": "",
                "citations": [],
                "tool_trace": [],
                "duration_ms": int((perf_counter() - started) * 1000),
                "error": f"{type(exc).__name__}: {exc}",
            }
    report["metrics"] = score_agent_case(report, gold)
    report["wall_clock_seconds"] = round(perf_counter() - started, 3)
    return report


def _summarize(report: dict[str, Any]) -> str:
    cid = report.get("case_id")
    passed = bool((report.get("metrics") or {}).get("passed"))
    status = "PASS" if passed else "FAIL"
    body = json.dumps(report.get("metrics"), indent=2)
    return f"## {cid} — {status}\n\n```json\n{body}\n```"


def _cli(
    path: Path = typer.Argument(..., exists=True, readable=True),
    suite: bool = typer.Option(False, "--suite"),
    tier: str = typer.Option("agent_tools_mini", "--tier"),
    live_runtime: bool = typer.Option(
        True,
        "--live-runtime/--no-live-runtime",
        help="Default: call production agent stack. Use --no-live-runtime for deterministic mock.",
    ),
    mock_runtime: bool = typer.Option(
        False,
        "--mock-runtime",
        help="Deprecated alias for --no-live-runtime (mock answers).",
    ),
    json_out: Path | None = typer.Option(None, "--json-out"),
    md_out: Path | None = typer.Option(None, "--md-out"),
) -> None:
    settings = get_settings()
    use_mock = mock_runtime or (not live_runtime)
    if suite:
        cases = discover_agent_case_dirs(path, tier=tier)
        if not cases:
            raise typer.Exit(code=1)
        payload = run_suite_cli_flow(
            title="Agent tools benchmark suite",
            cases=cases,
            settings=settings,
            run_one=lambda p: run_agent_case(p, mock_runtime=use_mock),
            summarize=_summarize,
            json_out=json_out,
            md_out=md_out,
            summary_from_reports=lambda reports: {
                "all_passed": all(bool((r.get("metrics") or {}).get("passed")) for r in reports),
                "agent_tools_eval": True,
                "latency_p95_ms": sorted([int(r.get("duration_ms") or 0) for r in reports])[
                    max(len(reports) - 1, 0)
                ],
                "avg_unnecessary_tool_calls": round(
                    sum(float((r.get("metrics") or {}).get("unnecessary_tool_calls") or 0) for r in reports)
                    / max(len(reports), 1),
                    4,
                ),
            },
        )
        if not bool(payload.get("summary", {}).get("all_passed", False)):
            raise typer.Exit(code=1)
        return
    report = run_agent_case(path, mock_runtime=use_mock)
    run_single_case_json_outputs(
        report=report,
        settings=settings,
        summarize=_summarize,
        json_out=json_out,
        md_out=md_out,
    )
    if not bool((report.get("metrics") or {}).get("passed")):
        raise typer.Exit(code=1)


def main() -> None:
    typer.run(_cli)


if __name__ == "__main__":
    main()
