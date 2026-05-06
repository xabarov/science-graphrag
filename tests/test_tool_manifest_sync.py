"""Manifest registry must cover every tool exposed by the LangGraph registry (Wave B / CH3)."""

from __future__ import annotations

from unittest.mock import MagicMock

from science_graphrag.agent.tool_manifest import TOOL_MANIFEST, manifest_by_name
from science_graphrag.agent.tools import build_tool_registry
from science_graphrag.config import Settings


def test_build_tool_registry_names_match_tool_manifest() -> None:
    stores = MagicMock()
    reg = build_tool_registry(
        stores,
        Settings(agent_web_research_tools_enabled=True, agent_doi_resolver_tool_enabled=True),
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
    optional = {"web_search", "web_fetch", "doi_resolver"}
    assert man_names - reg_names <= optional


def test_manifest_by_name_is_complete() -> None:
    m = manifest_by_name()
    assert len(m) == len(TOOL_MANIFEST)
