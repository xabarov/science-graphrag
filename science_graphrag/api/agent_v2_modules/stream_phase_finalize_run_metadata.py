"""Assemble ``run_metadata`` for the agent finalize SSE phase."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain_core.messages import HumanMessage

from science_graphrag.agent.context.research_plan_session import (
    get_research_plan_snapshot_for_thread,
)
from science_graphrag.agent.debug_events_telemetry import (
    extract_runtime_telemetry_from_debug_events,
)
from science_graphrag.agent.graph.tracing import (
    extract_last_ok_tool_payload,
    extract_last_tool_payload_for_tool,
)
from science_graphrag.agent.runtime import (
    aggregate_agent_llm_usage,
    extract_last_brief_from_messages,
)
from science_graphrag.agent.subagents.lifecycle import subagent_lifecycle_enhanced_enabled
from science_graphrag.agent.subagents.runtime import merge_subagent_run_rows
from science_graphrag.agent.subagents.terminal_truth import (
    SPAWN_CANCEL_FAILURE_CODE_ON_DEADLINE,
    SPAWN_CANCEL_FAILURE_CODE_ON_RECURSION,
    SPAWN_CANCEL_TERMINAL_ON_DEADLINE,
    SPAWN_CANCEL_TERMINAL_ON_RECURSION,
)
from science_graphrag.api.agent_v2_modules.payloads import (
    apply_runtime_metadata_from_state,
    build_run_metadata,
    merge_hook_chain_events_into_run_metadata,
    thread_insight_audit_fragment,
)
from science_graphrag.api.agent_v2_modules.stream_lifecycle_state import (
    StreamLifecycleRequestContext,
)
from science_graphrag.api.agent_v2_modules.stream_phase_recovery import (
    patch_spawn_rows_on_parent_abort,
)


@dataclass(frozen=True)
class FinalizeRunMetadataRequest:
    """Inputs required to build run_metadata for finalize SSE."""

    ctx: StreamLifecycleRequestContext
    latest_full_state: dict[str, Any] | None
    envelope: dict[str, Any]
    max_tool_calls: int
    thread_id: str | None
    compact_payload: dict[str, Any] | None
    post_turn_compaction_wall_ms: int
    salvaged_after_deadline: bool
    salvaged_after_recursion_limit: bool
    recursion_limit_value: int | None
    prefetched_pdf_result: dict[str, Any] | None = None


def _collect_human_message_payloads(
    latest_full_state: dict[str, Any] | None, *, kind: str, inner_key: str
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(latest_full_state, dict):
        return out
    for _hm in latest_full_state.get("messages") or []:
        if not isinstance(_hm, HumanMessage):
            continue
        _ak = getattr(_hm, "additional_kwargs", None) or {}
        if not isinstance(_ak, dict):
            continue
        if _ak.get("kind") != kind:
            continue
        _inner = _ak.get(inner_key)
        if isinstance(_inner, dict):
            out.append(_inner)
    return out


def _merge_pdf_read_transport_fields(
    run_meta: dict[str, Any],
    *,
    prefetched_pdf_result: dict[str, Any] | None,
    latest_full_state: dict[str, Any] | None,
) -> None:
    """Expose stable PDF read diagnostics for SSE/UI/session sync (compact keys)."""
    pl: dict[str, Any] | None = None
    if isinstance(prefetched_pdf_result, dict) and prefetched_pdf_result:
        pl = dict(prefetched_pdf_result)
    elif isinstance(latest_full_state, dict):
        pl = extract_last_tool_payload_for_tool(
            list(latest_full_state.get("messages") or []),
            tool="read_external_pdf",
        )
    if not isinstance(pl, dict) or not pl:
        return
    aid = str(pl.get("artifact_id") or "").strip()
    if aid:
        run_meta["pdf_read_artifact_id"] = aid
    if "ok" in pl:
        run_meta["pdf_read_tool_ok"] = bool(pl.get("ok"))
    err = str(pl.get("error") or "").strip()
    if err:
        run_meta["pdf_read_tool_error"] = err[:240]
    if "cache_hit" in pl:
        run_meta["pdf_read_cache_hit"] = bool(pl.get("cache_hit"))
    if pl.get("durable_hit"):
        run_meta["pdf_read_durable_hit"] = True


def _debug_events_tail(latest_full_state: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(latest_full_state, dict):
        return []
    tail = (latest_full_state.get("debug_events") or [])[-50:]
    return [x for x in tail if isinstance(x, dict)]


def _collect_metadata_spawn_rows(
    latest_full_state: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(latest_full_state, dict):
        return []
    metadata = latest_full_state.get("metadata") or {}
    if not isinstance(metadata, dict):
        return []
    raw = metadata.get("subagent_spawn_rows")
    if not isinstance(raw, list):
        return []
    return [x for x in raw if isinstance(x, dict)]


def _patch_spawn_rows_on_parent_terminal(
    rows: list[dict[str, Any]],
    *,
    salvaged_after_deadline: bool,
    salvaged_after_recursion_limit: bool,
) -> list[dict[str, Any]]:
    if not rows:
        return rows
    if salvaged_after_deadline:
        return patch_spawn_rows_on_parent_abort(
            rows,
            terminal_state=SPAWN_CANCEL_TERMINAL_ON_DEADLINE,
            failure_code=SPAWN_CANCEL_FAILURE_CODE_ON_DEADLINE,
        )
    if salvaged_after_recursion_limit:
        return patch_spawn_rows_on_parent_abort(
            rows,
            terminal_state=SPAWN_CANCEL_TERMINAL_ON_RECURSION,
            failure_code=SPAWN_CANCEL_FAILURE_CODE_ON_RECURSION,
        )
    return patch_spawn_rows_on_parent_abort(
        rows,
        terminal_state="succeeded",
        failure_code=None,
    )


def _merge_result_payload_groups(
    run_meta: dict[str, Any], latest_full_state: dict[str, Any] | None
) -> None:
    groups = (
        ("subagent_task_notifications", "task_notification", "task_notification"),
        (
            "claim_verification_results",
            "claim_verification_result",
            "claim_verification_result",
        ),
        ("corpus_explore_results", "corpus_explore_result", "corpus_explore_result"),
        ("research_plan_results", "research_plan_result", "research_plan_result"),
    )
    for out_key, kind, inner_key in groups:
        rows = _collect_human_message_payloads(latest_full_state, kind=kind, inner_key=inner_key)
        if rows:
            run_meta[out_key] = rows


def _merge_pdf_backend_fields(
    run_meta: dict[str, Any],
    *,
    latest_full_state: dict[str, Any] | None,
    prefetched_pdf_result: dict[str, Any] | None,
) -> None:
    pf = prefetched_pdf_result
    if isinstance(pf, dict) and bool(pf.get("ok")):
        rb = pf.get("read_backend")
        if isinstance(rb, str) and rb.strip():
            run_meta["pdf_read_effective_read_backend"] = rb.strip()
        run_meta["pdf_read_fallback_used"] = bool(pf.get("fallback_used"))

    if "pdf_read_effective_read_backend" not in run_meta and isinstance(latest_full_state, dict):
        pl = extract_last_ok_tool_payload(
            list(latest_full_state.get("messages") or []),
            tool="read_external_pdf",
        )
        if isinstance(pl, dict):
            rb2 = pl.get("read_backend")
            if isinstance(rb2, str) and rb2.strip():
                run_meta["pdf_read_effective_read_backend"] = rb2.strip()
            if "fallback_used" in pl:
                run_meta["pdf_read_fallback_used"] = bool(pl.get("fallback_used"))


def _build_base_run_meta(
    req: FinalizeRunMetadataRequest,
    *,
    debug_events_tail: list[dict[str, Any]],
    messages: list[Any],
) -> dict[str, Any]:
    ctx = req.ctx
    run_meta: dict[str, Any] = build_run_metadata(
        settings=ctx.settings,
        max_tool_calls=req.max_tool_calls,
        run_kind=ctx.run_kind,
        graph_id=ctx.graph_id,
        thread_id=req.thread_id,
        extra={
            "product_path": req.envelope.get("product_path"),
            "product_markers": req.envelope.get("product_markers"),
            "debug_events": debug_events_tail,
        },
    )
    req_frag = getattr(ctx, "request_run_metadata_fragment", None)
    if isinstance(req_frag, dict) and req_frag:
        run_meta.update(dict(req_frag))
    run_meta.update(extract_runtime_telemetry_from_debug_events(debug_events_tail))
    merge_hook_chain_events_into_run_metadata(
        run_meta,
        extra_events=ctx.hook_chain_events,
        debug_events_tail=debug_events_tail,
    )
    stream_usage = aggregate_agent_llm_usage(messages) if messages else None
    if stream_usage:
        run_meta["usage"] = stream_usage
    if messages and bool(getattr(ctx.settings, "agent_brief_output_enabled", False)):
        brief = extract_last_brief_from_messages(messages)
        if isinstance(brief, str) and brief.strip():
            run_meta["brief"] = brief.strip()[:240]
    return run_meta


def _merge_compaction_and_insight_fields(
    run_meta: dict[str, Any], req: FinalizeRunMetadataRequest
) -> None:
    thread_id = req.thread_id
    settings = req.ctx.settings
    if req.ctx.post_compact_paper_sources_restored_initial is not None:
        run_meta["post_compact_paper_sources_restored_count"] = int(
            req.ctx.post_compact_paper_sources_restored_initial
        )
    if thread_id and req.compact_payload is not None:
        comp = req.compact_payload.get("compaction")
        if isinstance(comp, dict):
            run_meta["compaction"] = comp
            if isinstance(comp.get("digest_count"), int):
                run_meta["session_digest_count"] = comp["digest_count"]
        audit_stream = req.compact_payload.get("audit")
        if isinstance(audit_stream, dict):
            run_meta["compaction_audit"] = audit_stream
    ti_frag = thread_insight_audit_fragment(thread_id=thread_id, settings=settings)
    if ti_frag:
        run_meta.update(ti_frag)
    if thread_id:
        run_meta["post_turn_compaction_wall_ms"] = req.post_turn_compaction_wall_ms


def build_finalize_run_metadata(req: FinalizeRunMetadataRequest) -> dict[str, Any]:
    """Build the ``run_metadata`` object embedded in the ``final_answer`` SSE event."""
    ctx = req.ctx
    latest_full_state = req.latest_full_state
    settings = ctx.settings
    thread_id = req.thread_id
    debug_events_tail = _debug_events_tail(latest_full_state)
    messages = (
        list(latest_full_state.get("messages") or []) if isinstance(latest_full_state, dict) else []
    )
    run_meta = _build_base_run_meta(req, debug_events_tail=debug_events_tail, messages=messages)
    if req.salvaged_after_deadline:
        run_meta["salvaged_after_deadline"] = True
    if req.salvaged_after_recursion_limit:
        run_meta["salvaged_after_recursion_limit"] = True
        run_meta["recursion_limit"] = req.recursion_limit_value
    run_meta = apply_runtime_metadata_from_state(
        run_metadata=run_meta,
        state=latest_full_state if isinstance(latest_full_state, dict) else None,
    )
    meta_rows = _collect_metadata_spawn_rows(latest_full_state)
    meta_rows = _patch_spawn_rows_on_parent_terminal(
        meta_rows,
        salvaged_after_deadline=req.salvaged_after_deadline,
        salvaged_after_recursion_limit=req.salvaged_after_recursion_limit,
    )
    merged_subagent_runs = merge_subagent_run_rows(
        routing_rows=ctx.routing_subagent_ledger.to_run_rows(),
        spawned_rows=list(ctx.spawn_subagent_runtime.to_run_rows()) + meta_rows,
    )
    if merged_subagent_runs:
        run_meta["subagent_runs"] = merged_subagent_runs
    if ctx.parent_turn_id_str:
        run_meta["parent_turn_id"] = ctx.parent_turn_id_str
    run_meta["max_parallel_subagents"] = int(settings.agent_max_parallel_subagents)
    _merge_result_payload_groups(run_meta, latest_full_state)
    request_plan_mode = str(run_meta.get("request_agent_mode") or "").strip().lower() == "plan"
    if thread_id and (
        request_plan_mode or bool(getattr(settings, "agent_research_plan_tool_enabled", False))
    ):
        plan_snapshot = get_research_plan_snapshot_for_thread(str(thread_id).strip())
        if isinstance(plan_snapshot, dict):
            run_meta["research_plan"] = plan_snapshot
    sr3 = (
        latest_full_state.get("specialist_results_v3")
        if isinstance(latest_full_state, dict)
        else None
    )
    if isinstance(sr3, dict) and sr3:
        run_meta["specialist_results_v3"] = dict(sr3)
    run_meta["subagent_observability_lane"] = (
        "fork_v3_enhanced"
        if str(settings.agent_runtime).strip() == "langgraph_supervisor_v3"
        and subagent_lifecycle_enhanced_enabled(settings)
        else "legacy_routing_sse_only"
    )
    if isinstance(ctx.prompt_memory_audit_initial, dict) and ctx.prompt_memory_audit_initial:
        run_meta.update(ctx.prompt_memory_audit_initial)
    _merge_compaction_and_insight_fields(run_meta, req)

    _merge_pdf_backend_fields(
        run_meta,
        latest_full_state=latest_full_state,
        prefetched_pdf_result=req.prefetched_pdf_result,
    )
    _merge_pdf_read_transport_fields(
        run_meta,
        prefetched_pdf_result=req.prefetched_pdf_result,
        latest_full_state=latest_full_state,
    )
    return run_meta


__all__ = ["FinalizeRunMetadataRequest", "build_finalize_run_metadata"]
