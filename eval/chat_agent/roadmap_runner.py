"""Roadmap-aligned chat-agent regression harness (live agent + artifact capture)."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from time import perf_counter
from typing import Any

import typer

from eval.bench_common import benchmark_run_metadata
from eval.chat_agent.observability_audit import build_observability_trace_audit
from eval.chat_agent.phoenix_export import (
    phoenix_project_identifier,
    phoenix_ui_trace_url,
    try_fetch_phoenix_spans,
)
from eval.chat_agent.roadmap_metrics import score_roadmap_case
from eval.chat_agent.workspace_audit import audit_workspace_readiness
from science_graphrag.agent.runtime import AgentRunOutput, build_agent
from science_graphrag.api.deps import close_store_registry, init_store_registry
from science_graphrag.config import get_settings


def _is_transient_llm_failure(exc: BaseException) -> bool:
    """One retry for flaky provider / gateway errors during long suites."""

    text = f"{type(exc).__name__}:{exc!s}".lower()
    return any(x in text for x in ("502", "503", "504", "429", "timeout", "connection reset"))


def discover_roadmap_case_files(fixtures_root: Path, tier: str = "baseline") -> list[Path]:
    """Return roadmap JSON cases.

    ``tier`` = baseline (``cases/``), strict (``cases_strict/``), or all.
    """

    t = (tier or "baseline").strip().lower()
    out: list[Path] = []
    baseline_dir = fixtures_root / "cases"
    strict_dir = fixtures_root / "cases_strict"
    if t in ("baseline", "all") and baseline_dir.is_dir():
        out.extend(sorted(p for p in baseline_dir.glob("*.json") if p.is_file()))
    if t in ("strict", "all") and strict_dir.is_dir():
        out.extend(sorted(p for p in strict_dir.glob("*.json") if p.is_file()))
    if t not in ("baseline", "strict", "all") and baseline_dir.is_dir():
        out.extend(sorted(p for p in baseline_dir.glob("*.json") if p.is_file()))
    return out


def _output_to_dict(out: AgentRunOutput) -> dict[str, Any]:
    data: dict[str, Any] = {
        "answer": out.answer,
        "citations": out.citations,
        "tool_trace": [dict(x) for x in out.tool_trace],
        "answer_class": out.answer_class,
        "evidence_summary": out.evidence_summary,
        "warnings": list(out.warnings or []),
        "inventory": out.inventory,
        "relation_trace": out.relation_trace,
        "quote_candidates": out.quote_candidates,
        "idea_suggestions": out.idea_suggestions,
        "bibliography": out.bibliography,
        "debug_events": list(out.debug_events or []),
        "phoenix_trace_id": out.phoenix_trace_id,
        "thread_id": out.thread_id,
    }
    return data


def _mock_primary_tool(gold: dict[str, Any]) -> str:
    expect = gold.get("expect") if isinstance(gold.get("expect"), dict) else {}
    any_of = list(expect.get("tools_any_of") or [])
    if any_of:
        return str(any_of[0])
    return "workspace_overview"


def _mock_report(
    case_id: str, question: str, workspace_id: str | None, gold: dict[str, Any]
) -> dict[str, Any]:
    primary = _mock_primary_tool(gold)
    trace = [
        {
            "step": 1,
            "tool": primary,
            "args_summary": {"workspace_id": workspace_id},
            "row_count": 1,
            "duration_ms": 1,
            "truncated": False,
            "error": None,
        },
        {
            "step": 2,
            "tool": "final_answer",
            "args_summary": {"answer_chars": 20},
            "row_count": 1,
            "duration_ms": 1,
            "truncated": False,
            "error": None,
        },
    ]
    allowed = (
        gold.get("expect", {}).get("answer_classes_allowed")  # type: ignore[union-attr]
        if isinstance(gold.get("expect"), dict)
        else None
    )
    ac = "inventory"
    if isinstance(allowed, list) and allowed:
        ac = str(allowed[0])
    expect = gold.get("expect") if isinstance(gold.get("expect"), dict) else {}
    bib = None
    if expect.get("require_typed_bibliography"):
        bib = {"format": "gost", "entries": [{"stub": "mock-bibliography-entry"}]}
    rt = None
    if expect.get("require_relation_trace"):
        rt = {"edges": [{"type": "CITES", "from": "mock-a", "to": "mock-b"}]}

    out = AgentRunOutput(
        answer="mock",
        citations=[],
        tool_trace=trace,  # type: ignore[arg-type]
        answer_class=ac,
        phoenix_trace_id="0" * 32,
        bibliography=bib,
        relation_trace=rt,
    )
    od = _output_to_dict(out)
    return {
        "case_id": case_id,
        "question": question,
        "workspace_id": workspace_id,
        "turns": [{"question": question, "output": od}],
        "final_output": od,
        "tool_trace": trace,
        "duration_ms": 2,
    }


def run_roadmap_case(case_path: Path, *, mock_runtime: bool = False) -> dict[str, Any]:
    gold = json.loads(case_path.read_text(encoding="utf-8"))
    case_id = str(gold.get("case_id") or case_path.stem)
    workspace_id = str(gold.get("workspace_id") or "").strip() or None
    max_calls = gold.get("max_tool_calls")
    hint = gold.get("answer_class_hint")
    hint_s = str(hint).strip() if hint else None

    turns_spec = gold.get("turns")
    if isinstance(turns_spec, list) and turns_spec:
        turns_in = [str((t or {}).get("question") or "").strip() for t in turns_spec]
        turns_in = [q for q in turns_in if q]
    else:
        q = str(gold.get("question") or "").strip()
        turns_in = [q] if q else []

    started = perf_counter()
    if mock_runtime:
        report = _mock_report(case_id, turns_in[0] if turns_in else "", workspace_id, gold)
        if len(turns_in) > 1:
            # Deterministic multi-turn mock: repeat primary tool pattern per turn, merge traces.
            merged: list[dict[str, Any]] = []
            turn_blocks: list[dict[str, Any]] = []
            for i, q in enumerate(turns_in):
                sub = _mock_report(f"{case_id}_t{i}", q, workspace_id, gold)
                merged.extend(list(sub.get("tool_trace") or []))
                turn_blocks.append({"question": q, "output": sub["final_output"]})
            report["turns"] = turn_blocks
            report["tool_trace"] = merged
            report["final_output"] = turn_blocks[-1]["output"]
    elif not turns_in:
        report = {
            "case_id": case_id,
            "error": "empty_question",
            "tool_trace": [],
            "duration_ms": int((perf_counter() - started) * 1000),
        }
    else:
        settings = get_settings()
        report: dict[str, Any] | None = None
        for attempt in range(2):
            try:
                stores = init_store_registry(settings)
                agent = build_agent(settings=settings, stores=stores)
                thread_id = (
                    str(gold.get("thread_id") or "").strip() or f"roadmap-{uuid.uuid4().hex}"
                )
                max_tool = (
                    int(max_calls) if max_calls is not None else int(settings.agent_max_tool_calls)
                )
                turn_reports = []
                last_out: AgentRunOutput | None = None
                for q in turns_in:
                    last_out = agent.run(
                        question=q,
                        workspace_id=workspace_id,
                        max_tool_calls=max_tool,
                        answer_class_hint=hint_s,
                        thread_id=thread_id if len(turns_in) > 1 else None,
                    )
                    turn_reports.append({"question": q, "output": _output_to_dict(last_out)})
                assert last_out is not None
                merged_trace: list[dict[str, Any]] = []
                for tr in turn_reports:
                    merged_trace.extend(list((tr.get("output") or {}).get("tool_trace") or []))
                report = {
                    "case_id": case_id,
                    "workspace_id": workspace_id,
                    "thread_id": thread_id if len(turns_in) > 1 else None,
                    "turns": turn_reports,
                    "final_output": _output_to_dict(last_out),
                    "tool_trace": merged_trace,
                    "duration_ms": int((perf_counter() - started) * 1000),
                }
                break
            except Exception as exc:  # noqa: BLE001
                if attempt == 0 and _is_transient_llm_failure(exc):
                    continue
                report = {
                    "case_id": case_id,
                    "error": f"{type(exc).__name__}: {exc}",
                    "tool_trace": [],
                    "duration_ms": int((perf_counter() - started) * 1000),
                }
                break
            finally:
                close_store_registry()
        if report is None:
            report = {
                "case_id": case_id,
                "error": "internal_error:empty_report_after_retries",
                "tool_trace": [],
                "duration_ms": int((perf_counter() - started) * 1000),
            }

    report["metrics"] = score_roadmap_case(report, gold)
    report["wall_clock_seconds"] = round(perf_counter() - started, 3)
    report["case_path"] = str(case_path)
    return report


def write_case_artifacts(
    report: dict[str, Any],
    gold: dict[str, Any],
    out_dir: Path,
    *,
    fetch_phoenix: bool = False,
) -> None:
    case_id = str(report.get("case_id") or "case")
    case_dir = out_dir / "cases" / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "case_spec.json").write_text(
        json.dumps(gold, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    final = report.get("final_output") or report
    tid = final.get("phoenix_trace_id") if isinstance(final, dict) else None
    trace_audit: dict[str, Any] = {
        "case_id": case_id,
        "phoenix_trace_id": tid,
        "phoenix_ui_hint": phoenix_ui_trace_url(trace_id=tid) if tid else None,
        "tool_trace": report.get("tool_trace") or [],
        "diagnostics": (report.get("metrics") or {}).get("diagnostics"),
        "metrics": report.get("metrics"),
    }
    if fetch_phoenix and tid:
        session_hint = final.get("thread_id") if isinstance(final, dict) else None
        trace_audit["phoenix_http_snapshot"] = try_fetch_phoenix_spans(
            tid,
            session_id=str(session_hint).strip() if session_hint else None,
        )
    tool_tr = [x for x in (report.get("tool_trace") or []) if isinstance(x, dict)]
    obs = build_observability_trace_audit(
        tool_trace=tool_tr,
        phoenix_http_snapshot=(
            trace_audit.get("phoenix_http_snapshot")
            if isinstance(trace_audit.get("phoenix_http_snapshot"), dict)
            else None
        ),
    )
    trace_audit["observability"] = obs
    report["observability"] = obs
    report["metrics"] = score_roadmap_case(report, gold)
    trace_audit["diagnostics"] = (report.get("metrics") or {}).get("diagnostics")
    trace_audit["metrics"] = report.get("metrics")

    (case_dir / "trace_audit.json").write_text(
        json.dumps(trace_audit, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    # Full consolidated artifact for offline review
    bundle = {
        "case_spec": gold,
        "run": report,
        "trace_audit": trace_audit,
    }
    (case_dir / "case_result.json").write_text(
        json.dumps(bundle, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _summarize(report: dict[str, Any]) -> str:
    cid = report.get("case_id")
    passed = bool((report.get("metrics") or {}).get("passed"))
    status = "PASS" if passed else "FAIL"
    body = json.dumps(report.get("metrics"), indent=2)
    return f"## {cid} — {status}\n\n```json\n{body}\n```"


def _cli(
    fixtures: Path = typer.Option(
        Path("tests/fixtures/benchmarks/chat_agent_roadmap"),
        "--fixtures",
        exists=True,
        file_okay=False,
        readable=True,
    ),
    out: Path = typer.Option(Path("eval/results/chat-agent-roadmap-latest"), "--out"),
    skip_audit: bool = typer.Option(False, "--skip-audit"),
    mock_runtime: bool = typer.Option(False, "--mock-runtime"),
    fetch_phoenix: bool = typer.Option(False, "--fetch-phoenix"),
    case_filter: str | None = typer.Option(None, "--case"),
    tier: str = typer.Option("baseline", "--tier", help="baseline | strict | all"),
) -> None:
    # Live harness needs real OTel spans for ``phoenix_trace_id``; ``extraction_llm`` scope no-ops
    # agent chains (see ``science_graphrag/observability/spans/decorators.py``).
    trace_scope_before = os.environ.get("PHOENIX_TRACE_SCOPE")
    if not mock_runtime:
        os.environ["PHOENIX_TRACE_SCOPE"] = "full"

    settings = get_settings()
    manifest_path = fixtures / "baseline_workspace_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    workspace_id = str(manifest.get("workspace_id") or "").strip()
    out.mkdir(parents=True, exist_ok=True)

    audit_blob: dict[str, Any] | None = None
    if not skip_audit and not mock_runtime:
        stores = init_store_registry(settings)
        try:
            audit_blob = {
                "schema_version": 1,
                "workspace_audit": audit_workspace_readiness(
                    workspace_id=workspace_id,
                    stores=stores,
                ),
            }
        finally:
            close_store_registry()
        (out / "workspace_audit.json").write_text(
            json.dumps(audit_blob, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        st = str((audit_blob.get("workspace_audit") or {}).get("status") or "")
        if st == "blocked":
            raise typer.Exit(code=3)

    case_files = discover_roadmap_case_files(fixtures, tier=tier)
    if case_filter:
        case_files = [p for p in case_files if p.stem == case_filter or p.name == case_filter]
    if not case_files:
        raise typer.Exit(code=1)

    reports: list[dict[str, Any]] = []
    for path in case_files:
        rep = run_roadmap_case(path, mock_runtime=mock_runtime)
        gold = json.loads(path.read_text(encoding="utf-8"))
        write_case_artifacts(rep, gold, out, fetch_phoenix=fetch_phoenix)
        reports.append(rep)

    summary = {
        "schema_version": 1,
        "suite": "chat_agent_roadmap",
        "eval_tier": tier,
        "fixtures": str(fixtures),
        "workspace_id": workspace_id,
        "benchmark_run_metadata": benchmark_run_metadata(settings),
        "environment": {
            "PHOENIX_UI_BASE_URL": os.getenv("PHOENIX_UI_BASE_URL"),
            "PHOENIX_PROJECT_ID": os.getenv("PHOENIX_PROJECT_ID"),
            "PHOENIX_PROJECT_NAME": os.getenv("PHOENIX_PROJECT_NAME"),
            "phoenix_project_resolved": phoenix_project_identifier(),
            "PHOENIX_TRACE_SCOPE": os.getenv("PHOENIX_TRACE_SCOPE"),
            "PHOENIX_TRACE_SCOPE_before_harness": trace_scope_before,
        },
        "workspace_audit": (audit_blob or {}).get("workspace_audit"),
        "all_passed": all(bool((r.get("metrics") or {}).get("passed")) for r in reports),
        "cases": [
            {
                "case_id": r.get("case_id"),
                "passed": bool((r.get("metrics") or {}).get("passed")),
                "observability_passed": bool(
                    ((r.get("metrics") or {}).get("diagnostics") or {}).get(
                        "observability_passed", True
                    )
                ),
                "duration_ms": r.get("duration_ms"),
            }
            for r in reports
        ],
    }
    (out / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Chat agent roadmap suite",
        "",
        f"- **all_passed:** {summary['all_passed']}",
        f"- **workspace_id:** `{workspace_id}`",
        "",
    ]
    for r in reports:
        lines.append(_summarize(r))
    (out / "summary.md").write_text("\n".join(lines), encoding="utf-8")

    if not summary["all_passed"]:
        raise typer.Exit(code=1)


def main() -> None:
    typer.run(_cli)


if __name__ == "__main__":
    main()
