"""Epic B2/B3/B4: typed merge, claim verification policy, and trace signals."""

from __future__ import annotations

from science_graphrag.agent.graph.state import AgentState
from science_graphrag.agent.subagents.claim_verification_runtime import (
    create_claim_verification_can_use_tool,
)
from science_graphrag.agent.subagents.specialist_results_v3 import (
    append_claim_verification_leg,
    append_parent_tool_leg,
    empty_specialist_results_v3,
    serialize_for_writer,
)
from science_graphrag.agent.tool_execution_pipeline import build_tool_execution_node
from science_graphrag.config import Settings


def test_managed_report_skips_duplicate_directive_enrichment() -> None:
    from science_graphrag.agent.subagents.specialist_results_v3 import append_corpus_explore_leg

    text = (
        "Task outcome (short): Thin workspace coverage.\n"
        "Task outcome (detailed): Only metadata hits.\n"
        "Open limitations / next checks:\n"
        "- metadata_only evidence\n"
    )
    v3 = append_corpus_explore_leg(
        None,
        subagent_id="ce-1",
        text=text,
        terminal_state="succeeded",
        failure_code=None,
        issues=[],
    )
    directive = str((v3.get("merge") or {}).get("writer_directive") or "")
    assert "Open limitations:" not in directive
    assert (v3.get("merge") or {}).get("report_sections_present") is True


def test_corpus_explore_leg_populates_typed_merge_limitations() -> None:
    from science_graphrag.agent.subagents.specialist_results_v3 import append_corpus_explore_leg

    text = (
        "Task outcome (short): Thin workspace coverage.\n"
        "Task outcome (detailed): Only metadata hits for two papers.\n"
        "Open limitations / next checks:\n"
        "- metadata_only evidence\n"
        "- Next check: expand find_works query\n"
    )
    v3 = append_corpus_explore_leg(
        None,
        subagent_id="ce-1",
        text=text,
        terminal_state="succeeded",
        failure_code=None,
        issues=[],
    )
    merge = v3.get("merge") or {}
    assert merge.get("limitations")
    assert merge.get("next_checks")
    assert merge.get("report_sections_present") is True
    legs = v3.get("legs") or []
    assert isinstance(legs[0].get("managed_report"), dict)


def test_specialist_results_v3_merge_conflict_on_verdict_mismatch() -> None:
    v3 = empty_specialist_results_v3()
    v3 = append_parent_tool_leg(v3, specialist_id="retrieval_agent", tool_payloads=[{"ok": True}])
    v3 = append_claim_verification_leg(
        v3,
        subagent_id="cv-a",
        text="Scope: x\nResult: y\nKey sources: none\nVERDICT: PASS\n",
        terminal_state="succeeded",
        failure_code=None,
        issues=[],
    )
    v3 = append_claim_verification_leg(
        v3,
        subagent_id="cv-b",
        text="Scope: x\nResult: z\nKey sources: none\nVERDICT: FAIL\n",
        terminal_state="succeeded",
        failure_code=None,
        issues=[],
    )
    merge = v3.get("merge") or {}
    assert merge.get("conflict") is not None
    assert merge.get("evidence_origin") == "mixed"
    assert "CONFLICT" in str(merge.get("writer_directive") or "")


def test_serialize_for_writer_truncates() -> None:
    blob = append_parent_tool_leg(
        None,
        specialist_id="retrieval_agent",
        tool_payloads=[{"work_id": "w1"}],
    )
    s = serialize_for_writer(blob, max_chars=200)
    assert len(s) <= 200


def test_claim_verification_can_use_tool_denies_non_whitelisted() -> None:
    cb = create_claim_verification_can_use_tool(frozenset({"w1"}))
    st: AgentState = {  # type: ignore[assignment]
        "messages": [],
        "metadata": {},
        "specialist_results": {},
        "budget_remaining": 4,
    }
    assert cb(st, "cypher_query", {"args": {}}) is not None
    assert cb(st, "paper_profile", {"args": {"work_id": "w2"}}) is not None
    assert cb(st, "paper_profile", {"args": {"work_id": "w1"}}) is None


def test_build_tool_execution_node_respects_claim_verification_callback() -> None:
    from langchain_core.messages import AIMessage

    from science_graphrag.agent.tools.final_answer import _make_final_answer_tool

    cb = create_claim_verification_can_use_tool(None)
    node = build_tool_execution_node(
        tools=[_make_final_answer_tool()],
        settings=Settings(),
        sidechain_id="test-cv",
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
    raw = getattr(msgs[0], "content", "")
    assert "permission_denied" in str(raw)
