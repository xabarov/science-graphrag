"""Assemble ``run_metadata`` for the agent finalize SSE phase."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage

from science_graphrag.agent.debug_events_telemetry import (
    extract_runtime_telemetry_from_debug_events,
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


def build_finalize_run_metadata(
    *,
    ctx: StreamLifecycleRequestContext,
    latest_full_state: dict[str, Any] | None,
    envelope: dict[str, Any],
    max_tool_calls: int,
    thread_id: str | None,
    compact_payload: dict[str, Any] | None,
    post_turn_compaction_wall_ms: int,
    salvaged_after_deadline: bool,
    salvaged_after_recursion_limit: bool,
    recursion_limit_value: int | None,
) -> dict[str, Any]:
    """Build the ``run_metadata`` object embedded in the ``final_answer`` SSE event."""
    settings = ctx.settings
    parent_turn_id_str = ctx.parent_turn_id_str

    stream_usage: dict[str, int] | None = None
    if latest_full_state is not None:
        msgs_for_usage = list(latest_full_state.get("messages") or [])
        stream_usage = aggregate_agent_llm_usage(msgs_for_usage)
    run_meta: dict[str, Any] = build_run_metadata(
        settings=settings,
        max_tool_calls=max_tool_calls,
        run_kind=ctx.run_kind,
        graph_id=ctx.graph_id,
        thread_id=thread_id,
        extra={
            "product_path": envelope.get("product_path"),
            "product_markers": envelope.get("product_markers"),
            "debug_events": (
                (latest_full_state or {}).get("debug_events", [])[-50:]
                if isinstance(latest_full_state, dict)
                else []
            ),
        },
    )
    _req_frag = getattr(ctx, "request_run_metadata_fragment", None)
    if isinstance(_req_frag, dict) and _req_frag:
        run_meta.update(dict(_req_frag))
    debug_events_tail = (
        (latest_full_state or {}).get("debug_events", [])[-50:]
        if isinstance(latest_full_state, dict)
        else []
    )
    if isinstance(debug_events_tail, list):
        run_meta.update(
            extract_runtime_telemetry_from_debug_events(
                [x for x in debug_events_tail if isinstance(x, dict)]
            )
        )
    merge_hook_chain_events_into_run_metadata(
        run_meta,
        extra_events=ctx.hook_chain_events,
        debug_events_tail=(debug_events_tail if isinstance(debug_events_tail, list) else None),
    )
    if stream_usage:
        run_meta["usage"] = stream_usage
    if isinstance(latest_full_state, dict) and bool(
        getattr(settings, "agent_brief_output_enabled", False)
    ):
        _bf = extract_last_brief_from_messages(list(latest_full_state.get("messages") or []))
        if isinstance(_bf, str) and _bf.strip():
            run_meta["brief"] = _bf.strip()[:240]
    if salvaged_after_deadline:
        run_meta["salvaged_after_deadline"] = True
    if salvaged_after_recursion_limit:
        run_meta["salvaged_after_recursion_limit"] = True
        run_meta["recursion_limit"] = recursion_limit_value
    run_meta = apply_runtime_metadata_from_state(
        run_metadata=run_meta,
        state=latest_full_state if isinstance(latest_full_state, dict) else None,
    )
    _meta_spawn: list[dict[str, Any]] = []
    if isinstance(latest_full_state, dict):
        _m = latest_full_state.get("metadata") or {}
        if isinstance(_m, dict):
            _raw_sp = _m.get("subagent_spawn_rows")
            if isinstance(_raw_sp, list):
                _meta_spawn = [x for x in _raw_sp if isinstance(x, dict)]
    if _meta_spawn and salvaged_after_deadline:
        _meta_spawn = patch_spawn_rows_on_parent_abort(
            _meta_spawn,
            terminal_state=SPAWN_CANCEL_TERMINAL_ON_DEADLINE,
            failure_code=SPAWN_CANCEL_FAILURE_CODE_ON_DEADLINE,
        )
    if _meta_spawn and salvaged_after_recursion_limit:
        _meta_spawn = patch_spawn_rows_on_parent_abort(
            _meta_spawn,
            terminal_state=SPAWN_CANCEL_TERMINAL_ON_RECURSION,
            failure_code=SPAWN_CANCEL_FAILURE_CODE_ON_RECURSION,
        )
    if _meta_spawn and not salvaged_after_deadline and not salvaged_after_recursion_limit:
        _meta_spawn = patch_spawn_rows_on_parent_abort(
            _meta_spawn,
            terminal_state="succeeded",
            failure_code=None,
        )
    merged_subagent_runs = merge_subagent_run_rows(
        routing_rows=ctx.routing_subagent_ledger.to_run_rows(),
        spawned_rows=list(ctx.spawn_subagent_runtime.to_run_rows()) + _meta_spawn,
    )
    if merged_subagent_runs:
        run_meta["subagent_runs"] = merged_subagent_runs
    if parent_turn_id_str:
        run_meta["parent_turn_id"] = parent_turn_id_str
    run_meta["max_parallel_subagents"] = int(settings.agent_max_parallel_subagents)
    _tn_collect = _collect_human_message_payloads(
        latest_full_state, kind="task_notification", inner_key="task_notification"
    )
    if _tn_collect:
        run_meta["subagent_task_notifications"] = _tn_collect
    _cv_collect = _collect_human_message_payloads(
        latest_full_state,
        kind="claim_verification_result",
        inner_key="claim_verification_result",
    )
    if _cv_collect:
        run_meta["claim_verification_results"] = _cv_collect
    _ce_collect = _collect_human_message_payloads(
        latest_full_state,
        kind="corpus_explore_result",
        inner_key="corpus_explore_result",
    )
    if _ce_collect:
        run_meta["corpus_explore_results"] = _ce_collect
    _rp_collect = _collect_human_message_payloads(
        latest_full_state,
        kind="research_plan_result",
        inner_key="research_plan_result",
    )
    if _rp_collect:
        run_meta["research_plan_results"] = _rp_collect
    if thread_id and bool(getattr(settings, "agent_research_plan_tool_enabled", False)):
        from science_graphrag.agent.context.research_plan_session import (
            get_research_plan_snapshot_for_thread,
        )

        _rp_live = get_research_plan_snapshot_for_thread(str(thread_id).strip())
        if isinstance(_rp_live, dict):
            run_meta["research_plan"] = _rp_live
    _sr3 = (
        latest_full_state.get("specialist_results_v3")
        if isinstance(latest_full_state, dict)
        else None
    )
    if isinstance(_sr3, dict) and _sr3:
        run_meta["specialist_results_v3"] = dict(_sr3)
    run_meta["subagent_observability_lane"] = (
        "fork_v3_enhanced"
        if str(settings.agent_runtime).strip() == "langgraph_supervisor_v3"
        and subagent_lifecycle_enhanced_enabled(settings)
        else "legacy_routing_sse_only"
    )
    pm0 = ctx.prompt_memory_audit_initial
    if isinstance(pm0, dict) and pm0:
        run_meta.update(pm0)
    if ctx.post_compact_paper_sources_restored_initial is not None:
        run_meta["post_compact_paper_sources_restored_count"] = int(
            ctx.post_compact_paper_sources_restored_initial
        )
    if thread_id and compact_payload is not None:
        comp = compact_payload.get("compaction")
        if isinstance(comp, dict):
            run_meta["compaction"] = comp
            if isinstance(comp.get("digest_count"), int):
                run_meta["session_digest_count"] = comp["digest_count"]
        aud_stream = compact_payload.get("audit")
        if isinstance(aud_stream, dict):
            run_meta["compaction_audit"] = aud_stream
    ti_frag = thread_insight_audit_fragment(thread_id=thread_id, settings=settings)
    if ti_frag:
        run_meta.update(ti_frag)
    if thread_id:
        run_meta["post_turn_compaction_wall_ms"] = post_turn_compaction_wall_ms

    return run_meta


__all__ = ["build_finalize_run_metadata"]
