"""Tests for persisted JSON boolean coercion."""

import pytest

from science_graphrag.config import Settings
from science_graphrag.settings.snapshot_agent_tools import build_agent_tools_snapshot
from science_graphrag.settings.stored_bool import optional_stored_bool


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, None),
        (True, True),
        (False, False),
        (1, True),
        (0, False),
        (2, None),
        ("true", True),
        ("FALSE", False),
        ("  yes ", True),
        ("off", False),
        ("", None),
        ("maybe", None),
    ],
)
def test_optional_stored_bool(raw: object, expected: bool | None) -> None:
    """``optional_stored_bool`` matches the coercion table for edge inputs."""
    assert optional_stored_bool(raw) is expected


def test_build_agent_tools_snapshot_coerces_string_bools() -> None:
    """Snapshot persisted flags accept string booleans from JSON stores."""
    snap = build_agent_tools_snapshot(
        agent_tools_cfg={
            "external_research_default_enabled": "true",
            "agent_unpaywall_oa_tool_enabled": "0",
        },
        merged_settings=Settings(),
    )
    assert snap["external_research_default_enabled"] is True
    assert snap["agent_unpaywall_oa_tool_enabled"] is False
