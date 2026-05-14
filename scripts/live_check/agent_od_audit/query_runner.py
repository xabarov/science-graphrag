"""Single agent query execution for OD workspace E2E audit."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx

from agent_od_audit.bootstrap import ensure_paths as _ensure_paths
from agent_od_audit.bootstrap import extra_headers as _extra_headers
from agent_od_audit.retry_policy import should_retry_after_transport_flake


def tool_steps(trace: list[dict[str, Any]]) -> tuple[list[str], int]:
    names: list[str] = []
    for row in trace:
        if not isinstance(row, dict):
            continue
        t = row.get("tool")
        if t:
            names.append(str(t))
    non_session = [n for n in names if n != "session_init"]
    return names, len(non_session)


def runtime_attribution_from_runtime_id(runtime_id: Any) -> tuple[str | None, str | None]:
    rt = str(runtime_id or "").strip()
    if rt in {"retrieval_v1", "langgraph_research_v1"}:
        return "single_agent_research", "single_agent_react"
    if rt == "langgraph_supervisor_v1":
        return "supervisor_specialists", "supervisor_graph"
    if rt == "langgraph_supervisor_v3":
        return "supervisor_specialists_v3", "supervisor_graph_v3"
    return None, None


def run_single_query(  # pylint: disable=too-many-arguments,too-many-locals
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
    extract_span_names_for_trace_fn: Callable[[Any, str], list[str]],
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
    except httpx.HTTPStatusError as exc:
        case_report["error"] = str(exc)
        if int(exc.response.status_code) in {502, 503, 504, 524}:
            case_report["retryable_provider_flake"] = True
        return case_report, False
    except (httpx.ReadTimeout, httpx.WriteTimeout, httpx.ConnectTimeout) as exc:
        case_report["error"] = str(exc)
        case_report["retryable_provider_flake"] = True
        return case_report, False
    except Exception as exc:  # noqa: BLE001
        case_report["error"] = str(exc)
        if should_retry_after_transport_flake({"http_ok": False, "error": str(exc)}):
            case_report["retryable_provider_flake"] = True
        return case_report, False

    case_report["http_ok"] = True
    trace = data.get("tool_trace") or []
    if not isinstance(trace, list):
        trace = []
    case_report["tool_trace"] = trace
    case_report["thread_id"] = data.get("thread_id")
    names, n_steps = tool_steps(trace)
    case_report["tool_names"] = names
    case_report["tool_steps_non_session"] = n_steps
    case_report["edge_search_zero_row_max_streak"] = edge_search_zero_row_max_streak(trace)
    case_report["paper_profile_max_consecutive_same_work_id"] = (
        paper_profile_max_consecutive_same_work_id(trace)
    )
    case_report["cypher_query_error_count"] = cypher_query_error_count(trace)
    case_report["duration_ms"] = data.get("duration_ms")
    raw_warns = data.get("warnings") or []
    case_report["warnings"] = raw_warns if isinstance(raw_warns, list) else []
    run_meta = data.get("run_metadata") if isinstance(data.get("run_metadata"), dict) else {}
    case_report["run_metadata"] = run_meta
    markers_raw = data.get("product_markers") or []
    markers: set[str] = set()
    if isinstance(markers_raw, list):
        markers = {str(x).strip() for x in markers_raw if str(x).strip()}
    warn_set = {str(x).strip() for x in case_report["warnings"]}
    if "retryable_provider_flake" in warn_set or "retryable_provider_flake" in markers:
        case_report["retryable_provider_flake"] = True
    elif run_meta.get("agent_sync_error"):
        from science_graphrag.api.agent_v2_modules.errors import (  # pylint: disable=import-outside-toplevel
            is_retryable_provider_error_class,
        )

        if is_retryable_provider_error_class(str(run_meta.get("error_class") or "")):
            case_report["retryable_provider_flake"] = True
    run_kind = str(run_meta.get("run_kind") or "").strip() or None
    graph_id = str(run_meta.get("graph_id") or "").strip() or None
    if run_kind is None or graph_id is None:
        derived_run_kind, derived_graph_id = runtime_attribution_from_runtime_id(
            run_meta.get("agent_runtime")
        )
        run_kind = run_kind or derived_run_kind
        graph_id = graph_id or derived_graph_id
    case_report["run_kind"] = run_kind
    case_report["graph_id"] = graph_id
    if run_meta:
        case_report["tool_search_shortlist_ratio_avg"] = run_meta.get(
            "tool_search_shortlist_ratio_avg"
        )
        case_report["tool_search_deferred_schema_events"] = run_meta.get(
            "tool_search_deferred_schema_events"
        )
        case_report["budget_stop_reasons"] = run_meta.get("budget_stop_reasons") or []
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
        span_names = extract_span_names_for_trace_fn(snap.get("payload"), tid)
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
