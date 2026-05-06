"""Unit tests for product surface tools (research plan, ask-user, brief, MCP deny, monitor)."""

from __future__ import annotations

import json

import pytest

from science_graphrag.agent.context.research_plan_session import merge_research_plan_items
from science_graphrag.agent.context.session_store import clear_session_store_for_tests
from science_graphrag.agent.context.user_structured_answer import (
    consume_user_structured_answer_for_thread,
)
from science_graphrag.agent.graph.state import build_initial_agent_state
from science_graphrag.agent.runtime import extract_last_brief_from_messages
from science_graphrag.agent.tools.mcp_surface import _server_denied
from science_graphrag.agent.tools.product_interaction_tools import build_product_interaction_tools
from science_graphrag.agent.tools.runtime_monitor_surface import (
    clear_runtime_monitor_snapshots_for_tests,
    register_runtime_monitor_snapshot,
)
from science_graphrag.agent.context.session_backend import get_session_memory_backend
from science_graphrag.config import Settings
from langchain_core.messages import ToolMessage
from science_graphrag.agent.tools.lsp_surface import (
    _decode_lsp_messages_from_text,
    _encode_lsp_message,
)
from science_graphrag.agent.tools.product_interaction_tools import AskUserQuestionArgs


@pytest.fixture(autouse=True)
def _clear_sessions():
    clear_session_store_for_tests()
    clear_runtime_monitor_snapshots_for_tests()
    yield
    clear_session_store_for_tests()
    clear_runtime_monitor_snapshots_for_tests()


def test_merge_research_plan_items_persists() -> None:
    tid = "thr-plan-1"
    get_session_memory_backend().patch_session_meta(tid, patch={"session_meta_seed": True})
    merge_research_plan_items(
        tid,
        [{"id": "1", "content": "Read papers", "status": "in_progress"}],
    )
    ent = get_session_memory_backend().get_session_copy(tid)
    plan = ent.get("session_meta", {}).get("research_plan")
    assert isinstance(plan, dict)
    assert len(plan.get("items") or []) == 1
    assert plan["items"][0]["id"] == "1"


def test_consume_user_structured_answer_clears_pending() -> None:
    tid = "thr-ask-1"
    get_session_memory_backend().patch_session_meta(
        tid,
        patch={
            "pending_user_question": {
                "request_id": "rid-1",
                "questions": [{"id": "q1", "prompt": "Pick", "options": [{"id": "a", "label": "A"}]}],
                "created_at": 1.0,
            }
        },
    )
    st = Settings(agent_ask_user_question_tool_enabled=True)
    evs, sfx = consume_user_structured_answer_for_thread(
        tid,
        {"request_id": "rid-1", "answers": [{"question_id": "q1", "selected_option_ids": ["a"]}]},
        settings=st,
    )
    assert any(e.get("type") == "user_answered" for e in evs)
    assert sfx and "user_structured_answer" in sfx
    ent = get_session_memory_backend().get_session_copy(tid)
    assert ent.get("session_meta", {}).get("pending_user_question") is None


def test_build_initial_agent_state_includes_user_answer_debug() -> None:
    tid = "thr-ask-2"
    get_session_memory_backend().patch_session_meta(
        tid,
        patch={
            "pending_user_question": {
                "request_id": "rid-2",
                "questions": [],
                "created_at": 1.0,
            }
        },
    )
    st = Settings(agent_ask_user_question_tool_enabled=True, agent_runtime="langgraph_research_v1")
    out = build_initial_agent_state(
        question="Continue",
        workspace_id=None,
        max_tool_calls=5,
        agent_runtime="langgraph_research_v1",
        thread_id=tid,
        settings=st,
        user_structured_answer={
            "request_id": "rid-2",
            "answers": [{"question_id": "q1", "selected_option_ids": ["x"]}],
        },
    )
    dbg = list(out.get("debug_events") or [])
    assert any(d.get("type") == "user_answered" for d in dbg)


def test_mcp_server_denylist() -> None:
    st = Settings(agent_mcp_server_denylist=["evil"])
    assert _server_denied(st, "my_evil_server") is not None


def test_runtime_monitor_registry() -> None:
    from science_graphrag.agent.tools.runtime_monitor_surface import build_runtime_monitor_tools

    register_runtime_monitor_snapshot(
        "job-1",
        {
            "state": "running",
            "progress": 0.5,
            "last_heartbeat_at": "t0",
            "degraded": False,
            "error_tail": None,
        },
    )
    tools = build_runtime_monitor_tools(Settings(agent_runtime_monitor_tool_enabled=True))
    assert tools
    out = tools[0].invoke({"task_id": "job-1"})
    data = out if isinstance(out, dict) else json.loads(str(out))
    assert isinstance(data, dict)
    assert data.get("state") == "running"


def test_brief_tool_and_extract() -> None:
    tools = build_product_interaction_tools(Settings(agent_brief_output_enabled=True))
    brief_tool = next(t for t in tools if getattr(t, "name", "") == "brief")
    raw = brief_tool.invoke({"text": "x" * 300})
    payload = raw if isinstance(raw, dict) else json.loads(raw)
    assert len(payload.get("brief", "")) <= 240
    msg = ToolMessage(content=json.dumps(payload), tool_call_id="1", name="brief")
    assert extract_last_brief_from_messages([msg]) == payload.get("brief")


def test_research_plan_tool_requires_thread(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "science_graphrag.agent.runtime_context.get_agent_graph_thread_id",
        lambda: None,
    )
    tools = build_product_interaction_tools(Settings(agent_research_plan_tool_enabled=True))
    rp = next(t for t in tools if getattr(t, "name", "") == "research_plan_write")
    out = rp.invoke({"items": [{"id": "a", "content": "c", "status": "pending"}]})
    body = out if isinstance(out, dict) else json.loads(out)
    assert body.get("error") == "missing_thread_id"


def test_ask_user_question_requires_two_options_and_unique_ids() -> None:
    with pytest.raises(ValueError, match="at least 2 items"):
        AskUserQuestionArgs.model_validate(
            {
                "questions": [
                    {
                        "id": "q1",
                        "prompt": "Pick one",
                        "options": [{"id": "a", "label": "Only option"}],
                    }
                ]
            }
        )

    with pytest.raises(ValueError, match="duplicate option id"):
        AskUserQuestionArgs.model_validate(
            {
                "questions": [
                    {
                        "id": "q1",
                        "prompt": "Pick one",
                        "options": [
                            {"id": "a", "label": "A"},
                            {"id": "a", "label": "A again"},
                        ],
                    }
                ]
            }
        )

    with pytest.raises(ValueError, match="duplicate question id"):
        AskUserQuestionArgs.model_validate(
            {
                "questions": [
                    {
                        "id": "q1",
                        "prompt": "Pick one",
                        "options": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}],
                    },
                    {
                        "id": "q1",
                        "prompt": "Pick two",
                        "options": [{"id": "c", "label": "C"}, {"id": "d", "label": "D"}],
                    },
                ]
            }
        )


def test_lsp_message_framing_roundtrip() -> None:
    raw = _encode_lsp_message({"jsonrpc": "2.0", "id": "1", "result": {"ok": True}})
    msgs = _decode_lsp_messages_from_text(raw)
    assert msgs == [{"jsonrpc": "2.0", "id": "1", "result": {"ok": True}}]
