"""Contracts for canonical agent v2 run_metadata builders."""

from __future__ import annotations

from types import SimpleNamespace

from science_graphrag.api.agent_v2_modules.payloads import (
    apply_runtime_metadata_from_state,
    build_run_metadata,
    response_from_run,
)
from science_graphrag.config import Settings


def test_build_run_metadata_includes_canonical_base_fields() -> None:
    meta = build_run_metadata(
        settings=Settings(),
        max_tool_calls=7,
        run_kind="single_agent_research",
        graph_id="single_agent_react",
        thread_id="thr-1",
        extra={"custom_flag": True},
    )
    assert meta["agent_max_tool_calls"] == 7
    assert meta["run_kind"] == "single_agent_research"
    assert meta["graph_id"] == "single_agent_react"
    assert meta["thread_id"] == "thr-1"
    assert meta["custom_flag"] is True
    assert "resolved_chat_llm_model" in meta


def test_apply_runtime_metadata_from_state_overrides_runtime_attribution() -> None:
    run_meta = {"run_kind": "old_kind", "graph_id": "old_graph"}
    patched = apply_runtime_metadata_from_state(
        run_metadata=run_meta,
        state={
            "metadata": {
                "run_kind": "supervisor_specialists",
                "graph_id": "supervisor_graph",
                "react_total_hops": 3,
                "react_force_finalize": "budget_exhausted",
            }
        },
    )
    assert patched["run_kind"] == "supervisor_specialists"
    assert patched["graph_id"] == "supervisor_graph"
    assert patched["react_total_hops"] == 3
    assert patched["react_force_finalize"] == "budget_exhausted"


def test_apply_runtime_metadata_from_state_includes_parent_turn_and_parallel_cap() -> None:
    patched = apply_runtime_metadata_from_state(
        run_metadata={"run_kind": "x", "graph_id": "y"},
        state={
            "metadata": {
                "run_kind": "supervisor_specialists_v3",
                "graph_id": "supervisor_graph_v3",
                "parent_turn_id": "550e8400-e29b-41d4-a716-446655440000",
                "max_parallel_subagents": 4,
            }
        },
    )
    assert patched["parent_turn_id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert patched["max_parallel_subagents"] == 4
    assert patched["run_kind"] == "supervisor_specialists_v3"


def test_response_from_run_merges_brief_into_run_metadata() -> None:
    out = SimpleNamespace(
        answer="ok",
        citations=[],
        tool_trace=[],
        llm_usage=None,
        debug_events=[],
        phoenix_trace_id=None,
        thread_id="t1",
        warnings=[],
        answer_class="synthesis",
        evidence_summary=None,
        inventory=None,
        relation_trace=None,
        quote_candidates=None,
        idea_suggestions=None,
        bibliography=None,
        product_path=None,
        product_markers=[],
        prompt_memory_run_metadata=None,
        subagent_runs=None,
        subagent_task_notifications=None,
        subagent_observability_lane=None,
        hook_chain_events=None,
        brief="Short card for history",
    )
    resp = response_from_run(
        out,
        duration_ms=1,
        settings=Settings(),
        max_tool_calls=5,
    )
    assert resp.run_metadata.get("brief") == "Short card for history"
