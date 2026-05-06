"""Contracts for canonical agent v2 run_metadata builders."""

from __future__ import annotations

from science_graphrag.api.agent_v2_modules.payloads import (
    apply_runtime_metadata_from_state,
    build_run_metadata,
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
