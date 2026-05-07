"""Train T4: isolated subagent state, policies, tool_use_summary, v3 legs."""

from __future__ import annotations

import json
from typing import Any

import pytest
from langchain_core.messages import AIMessage

import science_graphrag.agent.forked_runtime as fr
from science_graphrag.agent.debug_events_telemetry import (
    extract_runtime_telemetry_from_debug_events,
)
from science_graphrag.agent.graph.state import AgentState
from science_graphrag.agent.subagent_output_contract import (
    read_only_subagent_answer_matches_contract,
    research_plan_subagent_answer_matches_contract,
)
from science_graphrag.agent.subagents.corpus_explore_runtime import (
    create_corpus_explore_can_use_tool,
)
from science_graphrag.agent.subagents.isolated_subagent_state import (
    SUBAGENT_MEMORY_ISOLATION_VERSION,
    build_isolated_subagent_initial_state,
)
from science_graphrag.agent.subagents.research_plan_runtime import create_research_plan_can_use_tool
from science_graphrag.agent.subagents.specialist_results_v3 import (
    append_corpus_explore_leg,
    append_parent_tool_leg,
    append_research_plan_leg,
    empty_specialist_results_v3,
)
from science_graphrag.agent.tool_execution_pipeline import build_tool_execution_node
from science_graphrag.agent.tool_use_summary import (
    apply_tool_use_summary_to_tool_json_content,
    summarize_tool_result_payload_dict,
)
from science_graphrag.agent.tools.final_answer import _make_final_answer_tool
from science_graphrag.config import Settings


def test_isolated_subagent_state_flags_and_empty_messages() -> None:
    """Isolated child state clears messages and tags scratch memory."""
    st = Settings()
    out = build_isolated_subagent_initial_state(
        instruction_blob="Task: do X",
        workspace_id="ws-1",
        thread_id="thr-1",
        max_tool_calls=3,
        agent_runtime="langgraph_research_v1",
        settings=st,
        classifier="test_subagent",
        short_term_memory={"k": 1},
    )
    assert out.get("messages") == []
    meta = out.get("metadata") or {}
    assert meta.get("subagent_memory_isolation") == SUBAGENT_MEMORY_ISOLATION_VERSION
    assert meta.get("subagent_short_term_memory") == {"k": 1}


def test_corpus_explore_can_use_tool_denies_writes() -> None:
    """Non-whitelisted tools (e.g. cypher) are denied for corpus_explore."""
    cb = create_corpus_explore_can_use_tool()
    st: AgentState = {  # type: ignore[assignment]
        "messages": [],
        "metadata": {},
        "specialist_results": {},
        "budget_remaining": 4,
    }
    assert cb(st, "cypher_query", {"args": {}}) is not None
    assert cb(st, "workspace_inspect", {"args": {}}) is None


def test_research_plan_can_use_tool_write_gated() -> None:
    """research_plan_write is allowed only when product tool is enabled."""
    deny = create_research_plan_can_use_tool(allow_research_plan_write=False)
    allow = create_research_plan_can_use_tool(allow_research_plan_write=True)
    st: AgentState = {  # type: ignore[assignment]
        "messages": [],
        "metadata": {},
        "specialist_results": {},
        "budget_remaining": 4,
    }
    assert deny(st, "research_plan_write", {"args": {}}) is not None
    assert allow(st, "research_plan_write", {"args": {}}) is None


def test_read_only_contract_no_verdict() -> None:
    """Read-only subagent output must not include a VERDICT line."""
    good = "Scope: x\nResult: y\nKey sources: none\n"
    assert read_only_subagent_answer_matches_contract(good)
    bad = "Scope: x\nResult: y\nKey sources: z\nVERDICT: PASS\n"
    assert not read_only_subagent_answer_matches_contract(bad)


def test_research_plan_contract_headers() -> None:
    """Decomposition plan must include corpus/graph/writer subsections."""
    body = (
        "Scope: plan\n"
        "Result:\n"
        "Corpus sub-queries:\n- q1\n"
        "Graph sub-queries:\n- q2\n"
        "Writer spec:\n- cite heavy\n"
        "Key sources: w1\n"
    )
    assert research_plan_subagent_answer_matches_contract(body)


def test_specialist_results_v3_new_legs_merge() -> None:
    """Parent + corpus_explore + research_plan yields mixed evidence_origin."""
    v3 = append_parent_tool_leg(
        empty_specialist_results_v3(),
        specialist_id="retrieval_agent",
        tool_payloads=[{"ok": True}],
    )
    v3 = append_corpus_explore_leg(
        v3,
        subagent_id="ce-1",
        text="Scope: a\nResult: b\nKey sources: none\n",
        terminal_state="succeeded",
        failure_code=None,
        issues=[],
    )
    v3 = append_research_plan_leg(
        v3,
        subagent_id="rp-1",
        text=(
            "Scope: p\nResult:\nCorpus sub-queries:\n- x\n"
            "Graph sub-queries:\n- y\nWriter spec:\n- z\nKey sources: none\n"
        ),
        terminal_state="succeeded",
        failure_code=None,
        issues=[],
        research_plan_write_attempted=False,
        research_plan_write_ok=None,
    )
    merge = v3.get("merge") or {}
    assert merge.get("evidence_origin") == "mixed"


def test_tool_execution_respects_corpus_explore_callback() -> None:
    """ToolNode respects corpus_explore canUseTool deny layer."""
    cb = create_corpus_explore_can_use_tool()
    node = build_tool_execution_node(
        tools=[_make_final_answer_tool()],
        settings=Settings(),
        sidechain_id="test-ce",
        can_use_tool=cb,
    )
    bad_ai = AIMessage(
        content="",
        tool_calls=[
            {"name": "final_answer", "id": "tc1", "args": {"answer": "x", "citations": []}}
        ],
    )
    out = node(
        {
            "messages": [bad_ai],
            "metadata": {"turn_policy": {"tool_policy": "allow_tools"}},
            "budget_remaining": 2,
            "specialist_results": {},
        }
    )
    msgs = out.get("messages") or []
    assert msgs
    assert "permission_denied" in str(getattr(msgs[0], "content", ""))


def test_summarize_tool_result_payload_reduces_chars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Side-LLM path mocked; merged payload must shrink vs raw JSON."""
    big = {"ok": True, "items": [{"work_id": f"w{i}", "x": "y" * 200} for i in range(80)]}

    def _fake_side_llm(*_args: Any, **_kwargs: Any) -> Any:
        class _R:
            text = json.dumps(
                {
                    "schema_version": "tool_use_summary_v1",
                    "tool": "paper_quote_search",
                    "bullets": ["ok=true", "many items"],
                    "work_ids": ["w0"],
                    "numeric_facts": {},
                    "warnings": [],
                }
            )
            forked = True
            latency_ms = 1
            side_llm_cache_read_tokens = None
            side_llm_cache_creation_tokens = None
            side_llm_cache_read_ratio = None

        return _R()

    monkeypatch.setattr(fr, "run_side_llm_chat", _fake_side_llm)
    st = Settings()
    merged, meta = summarize_tool_result_payload_dict(
        settings=st, tool_name="paper_quote_search", payload=big
    )
    raw_before = json.dumps(big, ensure_ascii=True)
    raw_after = json.dumps(merged, ensure_ascii=True)
    assert len(raw_after) < len(raw_before)
    assert "_tool_use_summary" in merged
    assert meta.get("compression_ratio_vs_original") is not None


def test_apply_tool_use_summary_skips_below_threshold() -> None:
    """Below min char threshold, content is unchanged."""
    st = Settings(
        agent_tool_use_summary_enabled=True,
        agent_tool_use_summary_min_payload_chars=500_000,
    )
    small = json.dumps({"ok": True, "row_count": 1})
    out, meta = apply_tool_use_summary_to_tool_json_content(
        settings=st, tool_name="x", content=small
    )
    assert meta is None
    assert out == small


def test_debug_events_telemetry_tool_use_summary_batch() -> None:
    """tool_use_summary_batch rows aggregate into run_metadata telemetry."""
    tel = extract_runtime_telemetry_from_debug_events(
        [
            {
                "type": "tool_use_summary_batch",
                "ok": True,
                "count": 2,
                "rows": [
                    {"compression_ratio_vs_original": 4.0},
                    {"compression_ratio_vs_original": 2.0},
                ],
            }
        ]
    )
    assert tel.get("tool_use_summary_row_count") == 2
    assert tel.get("tool_use_summary_compression_ratio_avg") == 3.0
