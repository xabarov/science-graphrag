"""Tests for plan mode + worktree isolation tools (Epic P2.3 / P1.1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from science_graphrag.agent.context.session_backend import get_session_memory_backend
from science_graphrag.agent.context.session_store import clear_session_store_for_tests
from science_graphrag.agent.graph.state import build_initial_agent_state
from science_graphrag.agent.runtime_context import agent_graph_thread_id_scope
from science_graphrag.agent.tool_execution_pipeline import build_tool_execution_node
from science_graphrag.agent.tools.plan_mode_tools import build_plan_mode_tools
from science_graphrag.agent.tools.worktree_isolation_tools import build_worktree_isolation_tools
from science_graphrag.config import Settings


@pytest.fixture(autouse=True)
def _clear_sessions():
    clear_session_store_for_tests()
    yield
    clear_session_store_for_tests()


def test_plan_mode_tools_toggle_session(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tid = "thr-plan-surf-1"
    monkeypatch.chdir(tmp_path)
    tools = build_plan_mode_tools(Settings(agent_plan_mode_tools_enabled=True))
    assert {getattr(t, "name", "") for t in tools} == {"enter_plan_mode", "exit_plan_mode"}
    enter = next(t for t in tools if getattr(t, "name", "") == "enter_plan_mode")
    with agent_graph_thread_id_scope(tid):
        out = enter.invoke({"note": "probe"})
    body = out if isinstance(out, dict) else json.loads(out)
    assert body.get("ok") is True
    ent = get_session_memory_backend().get_session_copy(tid)
    pm = (ent.get("session_meta") or {}).get("plan_mode")
    assert isinstance(pm, dict) and pm.get("active") is True


def test_plan_mode_denies_high_risk_tools() -> None:
    tid = "thr-plan-deny-1"
    get_session_memory_backend().patch_session_meta(
        tid, patch={"plan_mode": {"active": True, "entered_at": 1.0}}
    )

    @tool("cypher_query")
    def cypher_query(_query: str = "") -> dict:
        """Stub graph tool (manifest risk high)."""
        return {"ok": True}

    st = Settings.model_construct()
    state = build_initial_agent_state(
        question="hi",
        workspace_id=None,
        max_tool_calls=4,
        agent_runtime="langgraph_research_v1",
        thread_id=tid,
        settings=st,
    )
    tools_node = build_tool_execution_node(tools=[cypher_query], settings=st)
    ai = AIMessage(content="", tool_calls=[{"name": "cypher_query", "id": "t1", "args": {}}])
    out = tools_node({**state, "messages": [ai]}, None)
    msgs = out.get("messages") or []
    assert msgs
    body = json.loads(str(getattr(msgs[0], "content", "") or ""))
    assert body.get("error") == "permission_denied"
    assert "plan_mode" in str(body.get("reason") or "")


def test_worktree_enter_exit_lifecycle(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tid = "thr-wt-1"
    monkeypatch.chdir(tmp_path)
    tools = build_worktree_isolation_tools(Settings(agent_worktree_tools_enabled=True))
    enter = next(t for t in tools if getattr(t, "name", "") == "enter_worktree")
    exit_wt = next(t for t in tools if getattr(t, "name", "") == "exit_worktree")
    with agent_graph_thread_id_scope(tid):
        out1 = enter.invoke({"label": "lane-a"})
        body1 = out1 if isinstance(out1, dict) else json.loads(out1)
        assert body1.get("ok") is True
        p = Path(str(body1.get("path")))
        assert p.is_dir()
        out2 = exit_wt.invoke({"remove_files": True})
        body2 = out2 if isinstance(out2, dict) else json.loads(out2)
        assert body2.get("ok") is True
        assert not p.exists()


def test_exit_worktree_does_not_delete_path_outside_sandbox(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Regression: never rmtree the configured root or paths outside the sandbox."""
    tid = "thr-wt-outside"
    sand = tmp_path / "sand"
    sand.mkdir()
    victim = tmp_path / "victim"
    victim.mkdir()
    monkeypatch.chdir(tmp_path)
    get_session_memory_backend().patch_session_meta(
        tid,
        patch={"agent_worktree": {"active": True, "path": str(victim), "label": "x"}},
    )
    tools = build_worktree_isolation_tools(
        Settings(agent_worktree_tools_enabled=True, agent_worktree_base_dir=str(sand))
    )
    exit_wt = next(t for t in tools if getattr(t, "name", "") == "exit_worktree")
    with agent_graph_thread_id_scope(tid):
        out = exit_wt.invoke({"remove_files": True})
    body = out if isinstance(out, dict) else json.loads(out)
    assert body.get("ok") is True
    assert body.get("removed_sandbox") is False
    assert victim.is_dir()


def test_enter_worktree_recreates_when_prior_path_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    tid = "thr-wt-stale"
    monkeypatch.chdir(tmp_path)
    stale = tmp_path / ".agent_worktrees" / tid / "gone"
    stale.parent.mkdir(parents=True, exist_ok=True)
    get_session_memory_backend().patch_session_meta(
        tid,
        patch={
            "agent_worktree": {
                "active": True,
                "path": str(stale),
                "label": "gone",
                "entered_at": 0.0,
            }
        },
    )
    tools = build_worktree_isolation_tools(Settings(agent_worktree_tools_enabled=True))
    enter = next(t for t in tools if getattr(t, "name", "") == "enter_worktree")
    with agent_graph_thread_id_scope(tid):
        out = enter.invoke({"label": "fresh"})
    body = out if isinstance(out, dict) else json.loads(out)
    assert body.get("ok") is True
    assert body.get("reused") is not True
    p = Path(str(body.get("path")))
    assert p.is_dir()


def test_enter_worktree_with_new_label_switches_sandbox(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    tid = "thr-wt-switch"
    monkeypatch.chdir(tmp_path)
    tools = build_worktree_isolation_tools(Settings(agent_worktree_tools_enabled=True))
    enter = next(t for t in tools if getattr(t, "name", "") == "enter_worktree")
    with agent_graph_thread_id_scope(tid):
        out1 = enter.invoke({"label": "lane-a"})
        body1 = out1 if isinstance(out1, dict) else json.loads(out1)
        out2 = enter.invoke({"label": "lane-b"})
        body2 = out2 if isinstance(out2, dict) else json.loads(out2)
    assert body1.get("ok") is True and body2.get("ok") is True
    assert body2.get("reused") is not True
    assert body1.get("label") == "lane-a"
    assert body2.get("label") == "lane-b"
    assert body1.get("path") != body2.get("path")
