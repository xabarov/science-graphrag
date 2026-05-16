"""Contracts for canonical agent v2 run_metadata builders."""

from __future__ import annotations

from types import SimpleNamespace

from langchain_core.messages import AIMessage

from science_graphrag.agent.runtime import RetrievalAgent
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
    assert meta.get("agent_pdf_read_backend_mode") == "hybrid"


def test_build_run_metadata_includes_openrouter_reference_pricing() -> None:
    settings = Settings(
        extraction_llm_base_url="https://openrouter.ai/api/v1",
        extraction_llm_model="openai/gpt-4o-mini",
        chat_llm_model="openai/gpt-4o-mini",
    )
    meta = build_run_metadata(
        settings=settings,
        max_tool_calls=5,
    )
    pricing = meta.get("openrouter_reference_pricing_usd_per_1m")
    assert isinstance(pricing, dict)
    chat = pricing.get("chat")
    assert isinstance(chat, dict)
    assert chat.get("model_id") == "openai/gpt-4o-mini"
    assert chat.get("prompt_usd_per_1m") == 0.15
    assert chat.get("completion_usd_per_1m") == 0.6


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


def test_response_from_run_aggregates_telemetry_from_full_debug_events() -> None:
    """Telemetry must include events even when they are outside the debug tail window."""
    early = {
        "type": "tool_use_summary_batch",
        "ok": True,
        "count": 1,
        "rows": [
            {
                "compression_ratio_vs_original": 2.5,
                "side_llm_cache_read_ratio": 0.4,
            }
        ],
    }
    late_noise = [{"type": "noise", "idx": i} for i in range(60)]
    out = SimpleNamespace(
        answer="ok",
        citations=[],
        tool_trace=[],
        llm_usage=None,
        debug_events=[early, *late_noise],
        phoenix_trace_id=None,
        thread_id="t2",
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
        brief=None,
    )
    resp = response_from_run(
        out,
        duration_ms=1,
        settings=Settings(),
        max_tool_calls=5,
    )
    meta = resp.run_metadata
    assert meta.get("tool_use_summary_batch_count") == 1
    assert meta.get("tool_use_summary_row_count") == 1
    assert meta.get("tool_use_summary_compression_ratio_avg") == 2.5
    assert meta.get("tool_use_summary_side_llm_cache_read_ratio_avg") == 0.4
    # Tail remains bounded even though telemetry used all events.
    assert len(meta.get("debug_events") or []) == 50


def test_retrieval_runtime_partial_salvage_patches_inflight_spawn_rows(monkeypatch) -> None:
    settings = Settings(agent_runtime="langgraph_supervisor_v3")
    stores = SimpleNamespace(
        neo4j=None,
        qdrant_chunks=None,
        qdrant_works=None,
        qdrant_claims=None,
        blob=None,
    )

    parent_turn_id = "pt-sync-partial-1"
    final_state = {
        "messages": [AIMessage(content="partial answer from salvage state")],
        "workspace_id": None,
        "citations": [],
        "tool_trace": [],
        "budget_remaining": 3,
        "routing_log": [],
        "debug_events": [],
        "specialist_results": {},
        "metadata": {
            "parent_turn_id": parent_turn_id,
            "subagent_spawn_rows": [
                {
                    "subagent_id": "ce-sync-1",
                    "parent_turn_id": parent_turn_id,
                    "spawn_reason": "corpus_explore",
                    "task_id": "task-sync-1",
                    "task_type": "corpus_explore",
                    "description": "Read-only corpus exploration child",
                    "execution_mode": "sync",
                    "fanout_slot": 1,
                    "task_status": "running",
                    "terminal_state": "running",
                    "latency_ms": 4,
                    "failure_code": None,
                    "kind": "spawned",
                    "merge_provenance": {
                        "strategy": "typed_specialist_results_v3",
                        "source_kind": "corpus_explore_result",
                    },
                    "output_pointer": "run_metadata.corpus_explore_results[0]",
                }
            ],
        },
    }

    monkeypatch.setattr(
        "science_graphrag.agent.runtime.build_retrieval_graph",
        lambda *_a, **_k: object(),
    )
    monkeypatch.setattr(
        "science_graphrag.agent.runtime.invoke_agent_graph_with_deadline_partial",
        lambda *_a, **_k: (final_state, True),
    )

    agent = RetrievalAgent(settings=settings, stores=stores)
    out = agent.run(
        question="q",
        workspace_id=None,
        max_tool_calls=6,
        answer_class_hint=None,
        thread_id=None,
        history_digest=None,
    )

    assert out.subagent_runs is not None
    spawned = next(
        row
        for row in out.subagent_runs
        if row.get("kind") == "spawned" and row.get("subagent_id") == "ce-sync-1"
    )
    assert spawned.get("terminal_state") == "timed_out"
    assert spawned.get("task_status") == "timed_out"
    assert spawned.get("failure_code") == "parent_timed_out"
    assert "agent_turn_deadline_partial_salvage" in (out.warnings or [])


def test_retrieval_runtime_normal_finalize_patches_inflight_spawn_rows(monkeypatch) -> None:
    settings = Settings(agent_runtime="langgraph_supervisor_v3")
    stores = SimpleNamespace(
        neo4j=None,
        qdrant_chunks=None,
        qdrant_works=None,
        qdrant_claims=None,
        blob=None,
    )

    parent_turn_id = "pt-sync-final-1"
    final_state = {
        "messages": [AIMessage(content="final answer from normal finalize")],
        "workspace_id": None,
        "citations": [],
        "tool_trace": [],
        "budget_remaining": 3,
        "routing_log": [],
        "debug_events": [],
        "specialist_results": {},
        "metadata": {
            "parent_turn_id": parent_turn_id,
            "subagent_spawn_rows": [
                {
                    "subagent_id": "ce-sync-final-1",
                    "parent_turn_id": parent_turn_id,
                    "spawn_reason": "corpus_explore",
                    "task_id": "task-sync-final-1",
                    "task_type": "corpus_explore",
                    "description": "Read-only corpus exploration child",
                    "execution_mode": "sync",
                    "fanout_slot": 1,
                    "task_status": "running",
                    "terminal_state": "running",
                    "latency_ms": 4,
                    "failure_code": None,
                    "kind": "spawned",
                    "merge_provenance": {
                        "strategy": "typed_specialist_results_v3",
                        "source_kind": "corpus_explore_result",
                    },
                    "output_pointer": "run_metadata.corpus_explore_results[0]",
                }
            ],
        },
    }

    monkeypatch.setattr(
        "science_graphrag.agent.runtime.build_retrieval_graph",
        lambda *_a, **_k: object(),
    )
    monkeypatch.setattr(
        "science_graphrag.agent.runtime.invoke_agent_graph_with_deadline_partial",
        lambda *_a, **_k: (final_state, False),
    )

    agent = RetrievalAgent(settings=settings, stores=stores)
    out = agent.run(
        question="q",
        workspace_id=None,
        max_tool_calls=6,
        answer_class_hint=None,
        thread_id=None,
        history_digest=None,
    )

    assert out.subagent_runs is not None
    spawned = next(
        row
        for row in out.subagent_runs
        if row.get("kind") == "spawned" and row.get("subagent_id") == "ce-sync-final-1"
    )
    assert spawned.get("terminal_state") == "succeeded"
    assert spawned.get("task_status") == "completed"
    assert spawned.get("failure_code") is None
