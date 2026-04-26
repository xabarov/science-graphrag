"""Manifest registry must cover every tool exposed by the LangGraph registry (Wave B / CH3)."""

from __future__ import annotations

from unittest.mock import MagicMock

from science_graphrag.agent.tool_manifest import TOOL_MANIFEST, manifest_by_name
from science_graphrag.agent.tools import build_tool_registry


def test_build_tool_registry_names_match_tool_manifest() -> None:
    stores = MagicMock()
    reg = build_tool_registry(stores)
    names = sorted({getattr(t, "name", "") for t in reg if getattr(t, "name", "")})
    man_names = sorted({e.name for e in TOOL_MANIFEST})
    assert names == man_names, f"registry {names} != manifest {man_names}"


def test_manifest_by_name_is_complete() -> None:
    m = manifest_by_name()
    assert len(m) == len(TOOL_MANIFEST)
