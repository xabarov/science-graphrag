#!/usr/bin/env python3
"""Live CV hot-topics audit for external research tools + Phoenix trace review."""

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

from eval.chat_agent.phoenix_export import extract_span_names_for_trace, try_fetch_phoenix_spans

_DEFAULT_BASE = "http://127.0.0.1:18787"
_DEFAULT_WORKSPACE = "ws-pilot-od"
_DEFAULT_TIMEOUT = 180.0

_CASES: list[dict[str, str]] = [
    {
        "id": "sam3_architecture",
        "topic": "SAM 3 promptable segmentation",
        "question": (
            "Найди свежую информацию о архитектуре SAM 3 в CV. "
            "Сначала сделай web search + web fetch по официальным и исследовательским источникам, "
            "затем используй Semantic Scholar для релевантной статьи, "
            "и если есть открытый PDF — попробуй прочитать PDF. "
            "В конце дай сжатый итог с ограничениями."
        ),
    },
    {
        "id": "open_vocabulary_detection",
        "topic": "Open-vocabulary object detection",
        "question": (
            "Собери обзор open-vocabulary object detection (2025-2026): лидирующие подходы, "
            "бенчмарки, ограничения. Используй web search + web fetch, затем Semantic Scholar "
            "для подтверждения минимум одной работы и попытайся прочитать ее OA PDF, если доступен."
        ),
    },
    {
        "id": "video_diffusion_world_models",
        "topic": "Video diffusion world models",
        "question": (
            "Найди горячие тренды video diffusion world models для computer vision. "
            "Проверь web источники, затем найди 1-2 научные работы через Semantic Scholar, "
            "и попробуй извлечь PDF-текст хотя бы для одной OA статьи."
        ),
    },
    {
        "id": "vla_robotics",
        "topic": "Vision-language-action for robotics",
        "question": (
            "Собери данные по vision-language-action моделям для робототехники: "
            "что реально работает, где bottlenecks. "
            "Используй web search/fetch + Semantic Scholar + PDF read (если OA есть). "
            "Финал — практическая оценка готовности."
        ),
    },
    {
        "id": "gaussian_splatting",
        "topic": "3D Gaussian Splatting",
        "question": (
            "Найди последние материалы по 3D Gaussian Splatting в CV и сравни с NeRF. "
            "Нужны web источники и научные источники через Semantic Scholar. "
            "Для одного ключевого paper попробуй прочитать PDF и дать конкретные выводы."
        ),
    },
    {
        "id": "efficient_edge_cv",
        "topic": "Efficient edge CV models",
        "question": (
            "Проведи web+scholar обзор efficient edge CV models (mobile/edge inference): "
            "архитектуры, ускорение, accuracy-latency tradeoff. "
            "Обязательно используй web search/fetch и Semantic Scholar; "
            "при наличии OA PDF — выполни чтение PDF."
        ),
    },
    {
        "id": "medical_foundation_vision",
        "topic": "Medical vision foundation models",
        "question": (
            "Найди горячие темы по medical vision foundation models (segmentation/diagnostics). "
            "Сначала web search/fetch, затем Semantic Scholar для новых статей, "
            "после этого попытайся прочитать OA PDF, если есть."
        ),
    },
    {
        "id": "synthetic_data_cv",
        "topic": "Synthetic data pipelines for CV",
        "question": (
            "Собери обзор synthetic data pipelines для CV обучения: где помогает, "
            "где domain gap. Используй web search + web fetch, затем Semantic Scholar, "
            "и попытайся прочитать PDF для одной ключевой работы."
        ),
    },
    {
        "id": "multimodal_pretraining_cv",
        "topic": "Multimodal pretraining for CV",
        "question": (
            "Найди актуальные результаты по multimodal pretraining для CV (2025-2026). "
            "Нужны web источники и научные подтверждения через Semantic Scholar, "
            "плюс попытка PDF read для OA статьи."
        ),
    },
    {
        "id": "document_vlm_ocr_free",
        "topic": "OCR-free VLM document understanding",
        "question": (
            "Собери информацию по OCR-free VLM для document understanding: "
            "layout reasoning, tables/charts, production risks. "
            "Используй web search/fetch, Semantic Scholar, и PDF read, если возможно."
        ),
    },
]


def _tool_names(tool_trace: list[dict[str, Any]]) -> list[str]:
    return [str(x.get("tool") or "") for x in tool_trace if isinstance(x, dict)]


def _tool_flags(tool_trace: list[dict[str, Any]]) -> dict[str, bool]:
    names = _tool_names(tool_trace)
    names_set = set(names)
    return {
        "web_search": "web_search" in names_set,
        "web_fetch": "web_fetch" in names_set,
        "final_answer": "final_answer" in names_set,
        "read_external_pdf": "read_external_pdf" in names_set,
        "semantic_scholar": any(n.startswith("semantic_scholar_") for n in names_set),
        "openalex": "openalex_works_search" in names_set,
        "arxiv": any(n.startswith("arxiv_") for n in names_set),
        "unpaywall": "unpaywall_lookup" in names_set,
    }


def _phoenix_names(trace_id: str, timeout: float) -> tuple[dict[str, Any], list[str]]:
    if not trace_id.strip():
        return {"ok": False, "error": "missing_trace_id"}, []
    snap = try_fetch_phoenix_spans(trace_id, timeout_s=min(20.0, timeout))
    meta = {"ok": bool(snap.get("ok")), "error": snap.get("error"), "url": snap.get("url")}
    if not snap.get("ok") or snap.get("payload") is None:
        return meta, []
    norm_tid = str(snap.get("trace_id") or trace_id).replace("-", "").lower()
    names = extract_span_names_for_trace(snap["payload"], norm_tid)
    return meta, names


def _evaluate_case(
    answer: str,
    citations: list[dict[str, Any]],
    flags: dict[str, bool],
    span_names: list[str],
) -> dict[str, Any]:
    issues: list[str] = []
    if not flags.get("web_search"):
        issues.append("missing_web_search")
    if not flags.get("web_fetch"):
        issues.append("missing_web_fetch")
    if not flags.get("final_answer"):
        issues.append("missing_final_answer_tool")
    if not answer.strip():
        issues.append("empty_answer")
    if len(citations) < 3:
        issues.append("few_citations")
    if not any(
        n in {"final_answer", "tool.final_answer"} or "tool.final_answer" in n for n in span_names
    ):
        issues.append("phoenix_missing_final_answer_span")
    return {
        "ok": not issues,
        "issues": issues,
        "answer_len": len(answer.strip()),
        "citations_count": len(citations),
    }


def _has_final_answer_span(span_names: list[str]) -> bool:
    return any(
        n in {"final_answer", "tool.final_answer"} or "tool.final_answer" in n for n in span_names
    )


def extract_terminal_reason_from_run_metadata(
    run_metadata: dict[str, Any] | None,
) -> str | None:
    """Read runtime-owned terminal reason from finalize run_metadata."""
    if not isinstance(run_metadata, dict):
        return None
    tr = str(run_metadata.get("terminal_reason") or "").strip()
    if tr:
        return tr
    fav = run_metadata.get("final_answer_validation")
    if isinstance(fav, dict):
        tr2 = str(fav.get("terminal_reason") or "").strip()
        if tr2:
            return tr2
    return None


def build_audit_diagnostics(
    *,
    tool_flags: dict[str, bool],
    span_names: list[str],
) -> dict[str, str]:
    """Audit-layer mismatch signals (independent from runtime terminal_reason)."""
    diagnostics: dict[str, str] = {}
    if not tool_flags.get("final_answer"):
        diagnostics["tool_trace_missing_final_answer"] = "missing_final_answer_tool"
    final_span_seen = _has_final_answer_span(span_names)
    if tool_flags.get("final_answer") and not final_span_seen:
        diagnostics["phoenix_missing_final_answer_span"] = "missing_span_but_tool_trace_present"
    elif not tool_flags.get("final_answer") and not final_span_seen:
        diagnostics["phoenix_missing_final_answer_span"] = "phoenix_missing_final_answer_span"
    return diagnostics


# Minimum next-slice gates from smolagents analysis doc (Phase 3 operator closeout).
NEXT_SLICE_GATES: dict[str, int] = {
    "runtime_ok_cases": 6,
    "tool_trace_ok_cases": 6,
    "phoenix_ok_cases": 5,
    "with_final_answer": 8,
    "generic_fallback_with_evidence_cases": 0,
}


def evaluate_next_slice_gates(coverage: dict[str, Any]) -> dict[str, Any]:
    """Compare coverage counters to minimum next-slice targets."""
    cov = coverage if isinstance(coverage, dict) else {}
    checks: dict[str, dict[str, Any]] = {}
    for key, minimum in NEXT_SLICE_GATES.items():
        if key == "generic_fallback_with_evidence_cases":
            actual = int(cov.get(key, 0) or 0)
            ok = actual <= int(minimum)
            checks[key] = {"ok": ok, "actual": actual, "maximum": minimum}
        else:
            actual = int(cov.get(key, 0) or 0)
            ok = actual >= int(minimum)
            checks[key] = {"ok": ok, "actual": actual, "minimum": minimum}
    return {
        "all_ok": all(bool(v.get("ok")) for v in checks.values()),
        "checks": checks,
    }


def evaluate_case_verdicts(
    *,
    http_status: int | None,
    error: str | None,
    answer: str,
    citations: list[dict[str, Any]],
    tool_flags: dict[str, bool],
    span_names: list[str],
) -> dict[str, Any]:
    """Split quality into runtime/tool-trace/phoenix verdicts."""
    runtime_issues: list[str] = []
    tool_trace_issues: list[str] = []
    phoenix_issues: list[str] = []

    if http_status is None:
        runtime_issues.append("request_failed")
    elif int(http_status) >= 400:
        runtime_issues.append("http_error")

    answer_text = str(answer or "").strip()
    if not answer_text:
        runtime_issues.append("empty_answer")
    fallback_text = "I could not produce a complete final answer for this turn."
    if answer_text.startswith(fallback_text):
        runtime_issues.append("fallback_answer")
    if len(citations) < 3:
        runtime_issues.append("few_citations")
    if error:
        runtime_issues.append("request_error")

    if not tool_flags.get("web_search"):
        tool_trace_issues.append("missing_web_search")
    if not tool_flags.get("web_fetch"):
        tool_trace_issues.append("missing_web_fetch")
    if not tool_flags.get("final_answer"):
        tool_trace_issues.append("missing_final_answer_tool")

    final_span_seen = _has_final_answer_span(span_names)
    if tool_flags.get("final_answer") and not final_span_seen:
        phoenix_issues.append("missing_span_but_tool_trace_present")
    if not tool_flags.get("final_answer") and not final_span_seen:
        phoenix_issues.append("phoenix_missing_final_answer_span")

    runtime_ok = not runtime_issues
    tool_trace_ok = not tool_trace_issues
    phoenix_ok = not phoenix_issues
    all_ok = runtime_ok and tool_trace_ok and phoenix_ok
    combined_issues = [*runtime_issues, *tool_trace_issues, *phoenix_issues]
    return {
        "ok": all_ok,
        "issues": combined_issues,
        "runtime": {"ok": runtime_ok, "issues": runtime_issues},
        "tool_trace": {"ok": tool_trace_ok, "issues": tool_trace_issues},
        "phoenix": {"ok": phoenix_ok, "issues": phoenix_issues},
        "answer_len": len(answer_text),
        "citations_count": len(citations),
    }


def _print_compare_delta(baseline_path: Path, current: dict[str, Any]) -> None:
    """Print coverage and next-slice gate deltas vs a prior CV JSON report."""
    if not baseline_path.is_file():
        print(f"compare-json: missing file {baseline_path}", flush=True)
        return
    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"compare-json: failed to read {baseline_path}: {exc}", flush=True)
        return
    b_cov = baseline.get("coverage") if isinstance(baseline.get("coverage"), dict) else {}
    c_cov = current.get("coverage") if isinstance(current.get("coverage"), dict) else {}
    keys = sorted(set(b_cov) | set(c_cov))
    print("--- compare-json delta (current - baseline) ---", flush=True)
    print(
        f"lane: baseline={baseline.get('lane_label', '?')} current={current.get('lane_label', '?')}",
        flush=True,
    )
    for key in keys:
        if key == "terminal_reason_distribution":
            continue
        try:
            delta = int(c_cov.get(key, 0) or 0) - int(b_cov.get(key, 0) or 0)
        except (TypeError, ValueError):
            continue
        if delta:
            print(f"  {key}: {b_cov.get(key, 0)} -> {c_cov.get(key, 0)} ({delta:+d})", flush=True)
    b_gates = (baseline.get("next_slice_gates") or {}).get("all_ok")
    c_gates = (current.get("next_slice_gates") or {}).get("all_ok")
    print(f"  next_slice_gates.all_ok: {b_gates} -> {c_gates}", flush=True)


def _write_markdown(report: dict[str, Any], out_md: Path) -> None:
    lines: list[str] = []
    lines.append("# External CV Hot Topics Live Audit")
    lines.append("")
    lines.append(f"- Base URL: `{report['base_url']}`")
    lines.append(f"- Workspace: `{report['workspace_id']}`")
    if report.get("lane_label"):
        lines.append(f"- Lane label: `{report['lane_label']}`")
    lines.append(
        f"- Passed: **{report['passed_cases']} / {report['total_cases']}**, failed: **{report['failed_cases']}**"
    )
    lines.append("")
    cov = report.get("coverage") or {}
    lines.append("## Coverage")
    lines.append(f"- web_search: {cov.get('with_web_search', 0)}")
    lines.append(f"- web_fetch: {cov.get('with_web_fetch', 0)}")
    lines.append(f"- final_answer: {cov.get('with_final_answer', 0)}")
    lines.append(f"- semantic_scholar: {cov.get('with_semantic_scholar', 0)}")
    lines.append(f"- read_external_pdf: {cov.get('with_pdf_read', 0)}")
    lines.append(
        f"- runtime_ok_cases: {cov.get('runtime_ok_cases', 0)}; "
        f"tool_trace_ok_cases: {cov.get('tool_trace_ok_cases', 0)}; "
        f"phoenix_ok_cases: {cov.get('phoenix_ok_cases', 0)}"
    )
    lines.append(
        f"- final_answer_validation_present: {cov.get('with_final_answer_validation', 0)}; "
        f"validation_fail_cases: {cov.get('validation_fail_cases', 0)}; "
        f"generic_fallback_with_evidence_cases: {cov.get('generic_fallback_with_evidence_cases', 0)}"
    )
    lines.append(f"- terminal_reason_present: {cov.get('with_terminal_reason', 0)}")
    dist = cov.get("terminal_reason_distribution") or {}
    if dist:
        lines.append(f"- terminal_reason_distribution: `{dist}`")
    gates = report.get("next_slice_gates") or {}
    if gates:
        lines.append("")
        lines.append("## Next-slice gates")
        lines.append(f"- all_ok: `{gates.get('all_ok')}`")
        for name, detail in (gates.get("checks") or {}).items():
            lines.append(f"- {name}: `{detail}`")
    lines.append("")
    lines.append("## Case Results")
    for case in report.get("cases") or []:
        lines.append(f"### {case['id']} — {case['topic']}")
        lines.append(f"- ok: `{case.get('ok')}`")
        verdicts = case.get("verdicts") or {}
        runtime_v = verdicts.get("runtime") or {}
        trace_v = verdicts.get("tool_trace") or {}
        phoenix_v = verdicts.get("phoenix") or {}
        lines.append(
            "- verdicts: "
            f"runtime={runtime_v.get('ok')} tool_trace={trace_v.get('ok')} phoenix={phoenix_v.get('ok')}"
        )
        lines.append(f"- trace id: `{case.get('phoenix_trace_id', '')}`")
        lines.append(f"- tools: `{', '.join(case.get('tool_names') or [])}`")
        quality = case.get("quality") or {}
        lines.append(
            f"- quality: answer_len={quality.get('answer_len', 0)}, citations={quality.get('citations_count', 0)}, issues={quality.get('issues', [])}"
        )
        fav = case.get("final_answer_validation")
        if isinstance(fav, dict):
            lines.append(
                f"- final_answer_validation: status={fav.get('status')} "
                f"reasons={fav.get('reasons')} evidence_present={fav.get('evidence_present')}"
            )
        tr = case.get("terminal_reason")
        if tr:
            lines.append(f"- terminal_reason: `{tr}`")
        audit_diag = case.get("audit_diagnostics")
        if isinstance(audit_diag, dict) and audit_diag:
            lines.append(f"- audit_diagnostics: `{audit_diag}`")
        lines.append(f"- answer preview: {str(case.get('answer_preview') or '')[:300]}")
        lines.append("")
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("AGENT_LIVE_BASE", _DEFAULT_BASE))
    parser.add_argument(
        "--workspace-id",
        default=(os.getenv("AGENT_LIVE_WORKSPACE_ID", _DEFAULT_WORKSPACE).strip() or None),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.getenv("AGENT_LIVE_TIMEOUT_SEC", str(_DEFAULT_TIMEOUT))),
    )
    parser.add_argument(
        "--out-json",
        default="eval/results/external-web-hot-topics-cv-live-2026-05-16.json",
    )
    parser.add_argument(
        "--out-md",
        default="eval/results/external-web-hot-topics-cv-live-2026-05-16.md",
    )
    parser.add_argument(
        "--out-phoenix-failures",
        default="",
        help="Optional JSONL with full span names for failing Phoenix checks.",
    )
    parser.add_argument(
        "--lane-label",
        default="baseline",
        help=(
            "Metadata label for this run (e.g. baseline vs experiment). "
            "Phase 6 A/B: run twice with API env "
            "SCIENCE_GRAPHRAG_AGENT_EXTERNAL_RESEARCH_TOOLCALLING_EXPERIMENT_ENABLED=0|1."
        ),
    )
    parser.add_argument(
        "--compare-json",
        default="",
        help="Optional path to a prior CV JSON report; prints coverage/gate deltas after this run.",
    )
    args = parser.parse_args()

    base = str(args.base_url).rstrip("/")
    out_json = Path(args.out_json)
    out_md = Path(args.out_md)
    out_failures = (
        Path(args.out_phoenix_failures)
        if str(args.out_phoenix_failures).strip()
        else out_json.with_name(f"{out_json.stem}_phoenix_failures.jsonl")
    )

    rows: list[dict[str, Any]] = []
    phoenix_failures: list[dict[str, Any]] = []
    with httpx.Client(timeout=float(args.timeout)) as client:
        for idx, case in enumerate(_CASES, start=1):
            print(f"[{idx}/{len(_CASES)}] {case['id']} ...", flush=True)
            payload: dict[str, Any] = {"question": case["question"], "web_research_enabled": True}
            if args.workspace_id:
                payload["workspace_id"] = args.workspace_id
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
                err_text = f"{type(exc).__name__}: {exc}"
                verdicts = evaluate_case_verdicts(
                    http_status=None,
                    error=err_text,
                    answer="",
                    citations=[],
                    tool_flags=_tool_flags([]),
                    span_names=[],
                )
                rows.append(
                    {
                        "id": case["id"],
                        "topic": case["topic"],
                        "question": case["question"],
                        "ok": False,
                        "http_status": None,
                        "error": err_text,
                        "elapsed_sec": round(time.time() - started, 2),
                        "tool_names": [],
                        "tool_flags": _tool_flags([]),
                        "phoenix_trace_id": "",
                        "phoenix": {"ok": False, "error": "missing_trace_id", "url": None},
                        "phoenix_span_names_sample": [],
                        "verdicts": verdicts,
                        "quality": verdicts,
                        "answer_preview": "",
                        "citations": [],
                    }
                )
                print(f"  -> ERROR: {type(exc).__name__}", flush=True)
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
            final_answer_validation = (
                run_metadata.get("final_answer_validation")
                if isinstance(run_metadata.get("final_answer_validation"), dict)
                else None
            )
            terminal_reason = extract_terminal_reason_from_run_metadata(run_metadata)
            trace_id = str(data.get("phoenix_trace_id") or "").strip()
            phoenix_meta, span_names = _phoenix_names(trace_id, timeout=float(args.timeout))
            audit_diagnostics = build_audit_diagnostics(
                tool_flags=flags,
                span_names=span_names,
            )
            verdicts = evaluate_case_verdicts(
                http_status=status,
                error=None,
                answer=answer,
                citations=[c for c in citations if isinstance(c, dict)],
                tool_flags=flags,
                span_names=span_names,
            )
            quality = _evaluate_case(answer, citations, flags, span_names)

            row = {
                "id": case["id"],
                "topic": case["topic"],
                "question": case["question"],
                "ok": bool(verdicts["ok"]),
                "http_status": status,
                "elapsed_sec": round(time.time() - started, 2),
                "tool_names": tool_names,
                "tool_flags": flags,
                "phoenix_trace_id": trace_id,
                "phoenix": phoenix_meta,
                "phoenix_span_names_sample": span_names[:80],
                "verdicts": verdicts,
                "quality": quality,
                "answer_preview": answer.strip()[:700],
                "citations": citations,
                "final_answer_validation": final_answer_validation,
                "terminal_reason": terminal_reason,
                "audit_diagnostics": audit_diagnostics,
            }
            rows.append(row)
            if not (verdicts.get("phoenix") or {}).get("ok", True):
                phoenix_failures.append(
                    {
                        "id": case["id"],
                        "topic": case["topic"],
                        "question": case["question"],
                        "phoenix_trace_id": trace_id,
                        "tool_names": tool_names,
                        "tool_flags": flags,
                        "verdicts": verdicts,
                        "full_span_names": span_names,
                    }
                )
            print(
                f"  -> ok={row['ok']} tools={len(tool_names)} answer_len={verdicts['answer_len']} issues={verdicts['issues']}",
                flush=True,
            )

    terminal_reason_dist: dict[str, int] = {}
    for r in rows:
        tr_key = str(r.get("terminal_reason") or "missing").strip() or "missing"
        terminal_reason_dist[tr_key] = terminal_reason_dist.get(tr_key, 0) + 1

    report: dict[str, Any] = {
        "lane_label": str(args.lane_label or "baseline").strip() or "baseline",
        "base_url": base,
        "workspace_id": args.workspace_id,
        "total_cases": len(_CASES),
        "passed_cases": sum(1 for r in rows if r.get("ok")),
        "failed_cases": sum(1 for r in rows if not r.get("ok")),
        "coverage": {
            "with_web_search": sum(
                1 for r in rows if (r.get("tool_flags") or {}).get("web_search")
            ),
            "with_web_fetch": sum(1 for r in rows if (r.get("tool_flags") or {}).get("web_fetch")),
            "with_final_answer": sum(
                1 for r in rows if (r.get("tool_flags") or {}).get("final_answer")
            ),
            "with_semantic_scholar": sum(
                1 for r in rows if (r.get("tool_flags") or {}).get("semantic_scholar")
            ),
            "with_pdf_read": sum(
                1 for r in rows if (r.get("tool_flags") or {}).get("read_external_pdf")
            ),
            "runtime_ok_cases": sum(
                1 for r in rows if ((r.get("verdicts") or {}).get("runtime") or {}).get("ok")
            ),
            "tool_trace_ok_cases": sum(
                1 for r in rows if ((r.get("verdicts") or {}).get("tool_trace") or {}).get("ok")
            ),
            "phoenix_ok_cases": sum(
                1 for r in rows if ((r.get("verdicts") or {}).get("phoenix") or {}).get("ok")
            ),
            "with_final_answer_validation": sum(
                1 for r in rows if isinstance(r.get("final_answer_validation"), dict)
            ),
            "validation_fail_cases": sum(
                1
                for r in rows
                if isinstance(r.get("final_answer_validation"), dict)
                and str((r.get("final_answer_validation") or {}).get("status") or "") == "fail"
            ),
            "generic_fallback_with_evidence_cases": sum(
                1
                for r in rows
                if isinstance(r.get("final_answer_validation"), dict)
                and "generic_fallback_with_evidence"
                in list((r.get("final_answer_validation") or {}).get("reasons") or [])
            ),
            "with_terminal_reason": sum(1 for r in rows if r.get("terminal_reason")),
            "terminal_reason_distribution": terminal_reason_dist,
        },
        "cases": rows,
    }
    report["next_slice_gates"] = evaluate_next_slice_gates(report["coverage"])

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_markdown(report, out_md)
    out_failures.parent.mkdir(parents=True, exist_ok=True)
    out_failures.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in phoenix_failures),
        encoding="utf-8",
    )

    compare_path = str(args.compare_json or "").strip()
    if compare_path:
        _print_compare_delta(Path(compare_path), report)

    print(
        json.dumps(
            {
                "written_json": str(out_json),
                "written_md": str(out_md),
                "written_phoenix_failures": str(out_failures),
                "lane_label": report.get("lane_label"),
                "passed": report["passed_cases"],
                "failed": report["failed_cases"],
                "coverage": report["coverage"],
                "next_slice_gates": report.get("next_slice_gates"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["failed_cases"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
