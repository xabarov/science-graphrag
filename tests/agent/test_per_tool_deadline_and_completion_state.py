"""Phase 6 regression tests: per-tool deadline + completion_state."""

from __future__ import annotations

import json
import time
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from science_graphrag.agent.coordination.question_features import (
    extract_question_features,
)
from science_graphrag.agent.coordination.route_planner import (
    planner_post_retrieval_handoff,
)
from science_graphrag.agent.subagents.specialist_results_v3 import (
    COMPLETION_STATE_VALUES,
    annotate_completion_state,
    append_parent_tool_leg,
    empty_specialist_results_v3,
)
from science_graphrag.agent.tool_execution_pipeline import (
    PER_TOOL_DEADLINE_REASON,
    build_tool_execution_node,
)


class _NoArgs(BaseModel):
    """Empty args schema for the slow-tool fixture."""


class _SlowTool(BaseTool):
    name: str = "slow_tool"
    description: str = "Sleeps to trigger the per-tool deadline."
    args_schema: type[BaseModel] = _NoArgs

    def _run(self, *_a, **_kw) -> str:  # type: ignore[override]
        time.sleep(2.0)
        return json.dumps({"ok": True})

    async def _arun(self, *_a, **_kw) -> str:  # type: ignore[override]
        return self._run()


def _build_settings(*, deadline: float = 0.0) -> MagicMock:
    s = MagicMock()
    s.agent_per_tool_call_timeout_seconds = deadline
    s.agent_allowed_tools_matrix_enabled = False
    s.agent_runtime = "langgraph_supervisor_v3"
    s.agent_tool_use_summary_enabled = False
    return s


def _build_state_with_one_tool_call(name: str = "slow_tool") -> dict:
    ai = AIMessage(
        content="",
        tool_calls=[{"name": name, "id": "c1", "args": {}, "type": "tool_call"}],
    )
    return {
        "messages": [ai],
        "metadata": {"turn_policy": {"tool_policy": "allow_tools"}},
        "workspace_id": "ws-1",
        "thread_id": "t-1",
        "specialist_results_v3": empty_specialist_results_v3(),
    }


def test_per_tool_deadline_fires_for_slow_tool() -> None:
    settings = _build_settings(deadline=0.5)
    node = build_tool_execution_node(tools=[_SlowTool()], settings=settings)
    state = _build_state_with_one_tool_call()

    out = node(state)
    msgs = out.get("messages") or []
    assert msgs
    tm = next((m for m in msgs if isinstance(m, ToolMessage)), None)
    assert tm is not None
    body = json.loads(str(tm.content))
    assert body.get("error") == PER_TOOL_DEADLINE_REASON
    debug = out.get("debug_events") or []
    assert any(
        ev.get("phase") == "deadline" and ev.get("code") == PER_TOOL_DEADLINE_REASON for ev in debug
    )


def test_per_tool_deadline_disabled_runs_tool_to_completion() -> None:
    """Sanity: when the cap is 0 the slow tool blocks (kept short for CI)."""

    settings = _build_settings(deadline=0.0)

    class _FastTool(BaseTool):
        name: str = "fast_tool"
        description: str = "Returns immediately."
        args_schema: type[BaseModel] = _NoArgs

        def _run(self, *_a, **_kw) -> str:  # type: ignore[override]
            return json.dumps({"ok": True, "row_count": 1})

        async def _arun(self, *_a, **_kw) -> str:  # type: ignore[override]
            return self._run()

    node = build_tool_execution_node(tools=[_FastTool()], settings=settings)
    state = _build_state_with_one_tool_call(name="fast_tool")
    out = node(state)
    msgs = out.get("messages") or []
    assert msgs
    debug = out.get("debug_events") or []
    assert all(ev.get("code") != PER_TOOL_DEADLINE_REASON for ev in debug)


def test_completion_state_default_payload_uses_any() -> None:
    payload = empty_specialist_results_v3()
    assert payload["merge"]["completion_state"] == "any_specialist_payload"


def test_annotate_completion_state_clamps_unknown_values() -> None:
    payload = annotate_completion_state(None, completion_state="not_a_real_state")
    assert payload["merge"]["completion_state"] == "any_specialist_payload"


def test_annotate_completion_state_records_known_value() -> None:
    payload = annotate_completion_state(
        empty_specialist_results_v3(), completion_state="minimal_bundle_ready"
    )
    assert payload["merge"]["completion_state"] == "minimal_bundle_ready"


def test_completion_state_overrides_substring_handoff_in_planner() -> None:
    feats = extract_question_features(
        question=(
            "Compare two detector families and produce a bibliography: use find_works "
            "twice, call paper_profile for two distinct work_ids, then format a GOST "
            "bibliography."
        ),
        workspace_id="ws-1",
    )
    # Substring features alone would withhold handoff (waiting for GOST tool).
    assert (
        planner_post_retrieval_handoff(
            features=feats, tool_counts={"find_works": 2, "paper_profile": 2}
        )
        is None
    )
    # But explicit completion signal forces the handoff.
    assert (
        planner_post_retrieval_handoff(
            features=feats,
            tool_counts={"find_works": 2, "paper_profile": 2},
            completion_state="minimal_bundle_ready",
        )
        == "retrieval_completion_minimal_bundle"
    )


def test_completion_state_inferred_from_legs() -> None:
    payload = append_parent_tool_leg(
        empty_specialist_results_v3(),
        specialist_id="retrieval_agent",
        tool_payloads=[{"row_count": 1}],
    )
    # No explicit annotation: derived from leg shape.
    assert payload["merge"]["completion_state"] in COMPLETION_STATE_VALUES


def test_supervisor_decision_uses_completion_state() -> None:
    from science_graphrag.agent.graph.supervisor_decisions import (
        compute_post_retrieval_handoff,
    )

    state = {
        "current_specialist": "retrieval_agent",
        "messages": [],
        "workspace_id": "ws-1",
        "metadata": {
            "raw_user_question": (
                "Compare evidence for two different object-detection works in this workspace."
            ),
            "turn_policy": {
                "tool_policy": "allow_tools",
                "route_plan": {
                    "schema_version": 1,
                    "steps": [{"specialist": "retrieval_agent"}],
                    "termination": {"rule_id": "writer_after_first_hop_completion"},
                },
            },
        },
        "specialist_results_v3": annotate_completion_state(
            empty_specialist_results_v3(), completion_state="minimal_bundle_ready"
        ),
    }
    settings = MagicMock()
    settings.agent_route_plan_post_retrieval_handoff_enabled = True

    reason = compute_post_retrieval_handoff(state=state, settings=settings)
    assert reason == "retrieval_completion_minimal_bundle"


def test_derive_retrieval_completion_state_web_search_only_is_insufficient() -> None:
    from science_graphrag.agent.coordination.route_planner import (
        derive_retrieval_completion_state,
    )

    feats = extract_question_features(
        question="поищи в интернете по теме object detection",
        workspace_id="ws-1",
    )
    cs = derive_retrieval_completion_state(
        features=feats,
        tool_counts={"web_search": 1},
        has_payloads=True,
    )
    assert cs == "evidence_insufficient"


def test_derive_retrieval_completion_state_web_fetch_ready() -> None:
    from science_graphrag.agent.coordination.route_planner import (
        derive_retrieval_completion_state,
    )

    feats = extract_question_features(
        question="what are people saying online about this topic?",
        workspace_id="ws-1",
    )
    cs = derive_retrieval_completion_state(
        features=feats,
        tool_counts={"web_search": 1, "web_fetch": 1},
        has_payloads=True,
    )
    assert cs == "minimal_bundle_ready"


def test_derive_retrieval_completion_state_arxiv_search_ready() -> None:
    from science_graphrag.agent.coordination.route_planner import (
        derive_retrieval_completion_state,
    )

    feats = extract_question_features(
        question="List arXiv preprints on object detection",
        workspace_id=None,
    )
    cs = derive_retrieval_completion_state(
        features=feats,
        tool_counts={"arxiv_search": 1},
        has_payloads=True,
    )
    assert cs == "minimal_bundle_ready"


def test_derive_retrieval_completion_state_arxiv_without_tool_is_insufficient() -> None:
    from science_graphrag.agent.coordination.route_planner import (
        derive_retrieval_completion_state,
    )

    feats = extract_question_features(
        question="Find arXiv papers about transformers",
        workspace_id=None,
    )
    cs = derive_retrieval_completion_state(
        features=feats,
        tool_counts={"find_works": 1},
        has_payloads=True,
    )
    assert cs == "evidence_insufficient"


def test_derive_retrieval_completion_state_pdf_requested_candidate_without_read_is_insufficient() -> None:
    from science_graphrag.agent.coordination.route_planner import (
        derive_retrieval_completion_state,
    )

    feats = extract_question_features(
        question="web search + semantic scholar and read pdf for one OA paper",
        workspace_id="ws-1",
    )
    assert feats.asks_for_pdf_read is True
    cs = derive_retrieval_completion_state(
        features=feats,
        tool_counts={"web_fetch": 1, "semantic_scholar_search": 1},
        has_payloads=True,
        tool_payloads=[{"item": {"oa_pdf_url": "https://example.org/paper.pdf"}}],
    )
    assert cs == "evidence_insufficient"


def test_derive_retrieval_completion_state_pdf_requested_read_attempt_allows_ready() -> None:
    from science_graphrag.agent.coordination.route_planner import (
        derive_retrieval_completion_state,
    )

    feats = extract_question_features(
        question="web search + semantic scholar and read pdf for one OA paper",
        workspace_id="ws-1",
    )
    assert feats.asks_for_pdf_read is True
    cs = derive_retrieval_completion_state(
        features=feats,
        tool_counts={"web_fetch": 1, "read_external_pdf": 1},
        has_payloads=True,
        tool_payloads=[
            {
                "web_sources": [
                    {
                        "url": "https://example.org/paper.pdf",
                        "source_tool": "read_external_pdf",
                    }
                ]
            }
        ],
    )
    assert cs == "minimal_bundle_ready"
