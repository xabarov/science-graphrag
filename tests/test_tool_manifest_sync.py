"""Manifest registry must cover every tool exposed by the LangGraph registry (Wave B / CH3)."""

from __future__ import annotations

from unittest.mock import MagicMock

from science_graphrag.agent.tool_manifest import TOOL_MANIFEST, manifest_by_name
from science_graphrag.agent.tools import build_tool_registry
from science_graphrag.config import Settings


def _all_optional_surface_settings() -> Settings:
    return Settings(
        agent_web_research_tools_enabled=True,
        agent_doi_resolver_tool_enabled=True,
        agent_mcp_tools_enabled=True,
        agent_lsp_tool_enabled=True,
        agent_runtime_monitor_tool_enabled=True,
        agent_research_plan_tool_enabled=True,
        agent_ask_user_question_tool_enabled=True,
        agent_brief_output_enabled=True,
        agent_plan_mode_tools_enabled=True,
        agent_worktree_tools_enabled=True,
    )


def test_build_tool_registry_names_match_tool_manifest() -> None:
    stores = MagicMock()
    reg = build_tool_registry(
        stores,
        _all_optional_surface_settings(),
    )
    names = sorted({getattr(t, "name", "") for t in reg if getattr(t, "name", "")})
    man_names = sorted({e.name for e in TOOL_MANIFEST})
    assert names == man_names, f"registry {names} != manifest {man_names}"


def test_default_registry_subset_of_manifest() -> None:
    """Optional web/DOI tools are manifest-only until feature flags enable them."""
    stores = MagicMock()
    reg = build_tool_registry(stores, Settings())
    reg_names = {getattr(t, "name", "") for t in reg if getattr(t, "name", "")}
    man_names = {e.name for e in TOOL_MANIFEST}
    assert reg_names <= man_names
    optional = {
        "web_search",
        "web_fetch",
        "doi_resolver",
        "call_mcp_tool",
        "list_mcp_resources",
        "fetch_mcp_resource",
        "mcp_auth",
        "lsp_tool",
        "runtime_monitor_get",
        "research_plan_write",
        "ask_user_question",
        "brief",
        "enter_plan_mode",
        "exit_plan_mode",
        "enter_worktree",
        "exit_worktree",
    }
    assert man_names - reg_names <= optional


def test_manifest_by_name_is_complete() -> None:
    m = manifest_by_name()
    assert len(m) == len(TOOL_MANIFEST)
