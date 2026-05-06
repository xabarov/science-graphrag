"""Disk agent registry + per-call permission filter (Train T3 §10.7)."""

from __future__ import annotations

import json
from pathlib import Path

from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from science_graphrag.agent.agent_registry import (
    build_system_prompt_for_disk_agent,
    disk_agent_definition_to_can_use_tool,
    load_disk_agent_definitions,
    parse_disk_agent_file,
)
from science_graphrag.agent.graph.state import build_initial_agent_state
from science_graphrag.agent.tool_execution_pipeline import build_tool_execution_node
from science_graphrag.config import Settings


def _fixture_agents_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures" / "agents"


def test_parse_librarian_fixture() -> None:
    path = _fixture_agents_dir() / "librarian.md"
    dfn = parse_disk_agent_file(path)
    assert dfn.name == "librarian"
    assert "cypher_query" in dfn.disallowed_tools
    assert "paper_profile" in dfn.tools
    assert "read_only" == dfn.permission_mode
    prompt = build_system_prompt_for_disk_agent(dfn)
    assert "librarian" in prompt
    assert "GOST" in prompt


def test_load_disk_agent_definitions_extra_user_dir() -> None:
    reg = load_disk_agent_definitions(
        workspace_agent_roots=(),
        extra_user_dirs=(_fixture_agents_dir(),),
    )
    assert "librarian" in reg
    assert reg["librarian"].source_path.endswith("librarian.md")


def test_parse_single_string_tool_entries_are_normalized(tmp_path: Path) -> None:
    path = tmp_path / "single.md"
    path.write_text(
        "---\n"
        "name: single\n"
        "tools: '  paper_profile  '\n"
        "disallowedTools: '  cypher_query  '\n"
        "---\n"
        "body\n",
        encoding="utf-8",
    )
    dfn = parse_disk_agent_file(path)
    assert dfn.tools == ("paper_profile",)
    assert dfn.disallowed_tools == ("cypher_query",)


def test_disk_agent_can_use_tool_denies_disallowed_and_non_whitelisted() -> None:
    path = _fixture_agents_dir() / "librarian.md"
    dfn = parse_disk_agent_file(path)
    cb = disk_agent_definition_to_can_use_tool(dfn)
    st = build_initial_agent_state(
        question="hi",
        workspace_id=None,
        max_tool_calls=4,
        agent_runtime="langgraph_research_v1",
        settings=Settings.model_construct(),
    )
    assert cb(st, "cypher_query", {}) is not None
    assert "disallowed" in (cb(st, "cypher_query", {}) or "")
    assert cb(st, "edge_search", {}) is not None
    assert "not_whitelisted" in (cb(st, "edge_search", {}) or "")
    assert cb(st, "paper_profile", {}) is None


def test_build_tool_execution_node_registry_callback_blocks_tool() -> None:
    path = _fixture_agents_dir() / "librarian.md"
    dfn = parse_disk_agent_file(path)
    can_use = disk_agent_definition_to_can_use_tool(dfn)

    @tool("cypher_query")
    def echo_tool(x: str = "") -> dict:
        """Stub graph tool."""
        return {"ok": True, "x": x}

    tools_node = build_tool_execution_node(
        tools=[echo_tool],
        settings=Settings.model_construct(),
        sidechain_id=None,
        can_use_tool=can_use,
    )
    state = build_initial_agent_state(
        question="q",
        workspace_id=None,
        max_tool_calls=4,
        agent_runtime="langgraph_research_v1",
        settings=Settings.model_construct(),
    )
    bad = AIMessage(
        content="",
        tool_calls=[{"name": "cypher_query", "id": "1", "args": {}}],
    )
    out = tools_node({**state, "messages": [bad]}, None)
    msgs = out.get("messages") or []
    assert msgs
    raw = str(getattr(msgs[0], "content", "") or "")
    body = json.loads(raw)
    assert body.get("error") == "permission_denied"
    assert "registry" in str(body.get("reason") or "")


def test_can_use_tool_callback_exception_yields_denial() -> None:
    def boom(_state, _name, _tc):
        raise RuntimeError("policy bug")

    @tool("idea_search")
    def idea_search(x: str = "") -> dict:
        """Stub."""
        return {"row_count": 0}

    tools_node = build_tool_execution_node(
        tools=[idea_search],
        settings=Settings.model_construct(),
        can_use_tool=boom,
    )
    state = build_initial_agent_state(
        question="q",
        workspace_id=None,
        max_tool_calls=4,
        agent_runtime="langgraph_research_v1",
        settings=Settings.model_construct(),
    )
    ai = AIMessage(
        content="",
        tool_calls=[{"name": "idea_search", "id": "1", "args": {}}],
    )
    out = tools_node({**state, "messages": [ai]}, None)
    body = json.loads(str(getattr(out["messages"][0], "content", "") or ""))
    assert body.get("error") == "permission_denied"
    assert "can_use_tool_callback_error" in str(body.get("reason") or "")
