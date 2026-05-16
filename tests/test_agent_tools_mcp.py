"""Unit tests for MCP operator snapshot helpers."""

from __future__ import annotations

from science_graphrag.config import Settings
from science_graphrag.settings.agent_tools_mcp import normalize_mcp_server_denylist
from science_graphrag.settings.snapshot_agent_tools import (
    _build_mcp_integrations_snapshot,
    _mcp_operator_state,
    build_agent_tools_snapshot,
)


def test_normalize_mcp_server_denylist_trims_and_caps() -> None:
    raw = ["  evil  ", "", "x" * 80, "ok"]
    out = normalize_mcp_server_denylist(raw)
    assert out == ["evil", "x" * 64, "ok"]


def test_mcp_operator_state_matrix() -> None:
    assert _mcp_operator_state(Settings(agent_mcp_tools_enabled=False)) == "disabled"
    assert (
        _mcp_operator_state(Settings(agent_mcp_tools_enabled=True, agent_mcp_http_base_url=None))
        == "unconfigured"
    )
    assert (
        _mcp_operator_state(
            Settings(
                agent_mcp_tools_enabled=True,
                agent_mcp_http_base_url="http://127.0.0.1:9999/rpc",
            )
        )
        == "configured"
    )


def test_build_mcp_integrations_snapshot_masks_host_only() -> None:
    st = Settings(
        agent_mcp_tools_enabled=True,
        agent_mcp_http_base_url="http://user:secret@adapter.internal:8080/rpc",
        agent_mcp_request_timeout_seconds=22.0,
        agent_mcp_server_denylist=["evil", "blocked"],
    )
    row = _build_mcp_integrations_snapshot(st)
    assert row["mcp_operator_state"] == "configured"
    assert row["mcp_base_url_host"] == "adapter.internal"
    assert row["mcp_request_timeout_seconds"] == 22.0
    assert row["mcp_server_denylist_count"] == 2
    assert row["mcp_auth_model"] == "delegation_required"
    assert row["mcp_adapter_url_source"] == "settings"
    assert "secret" not in str(row)


def test_agent_tools_snapshot_effective_includes_full_mcp_denylist() -> None:
    deny = [f"frag-{i}" for i in range(12)]
    st = Settings(agent_mcp_server_denylist=deny)
    snap = build_agent_tools_snapshot(agent_tools_cfg={}, merged_settings=st)
    eff = snap["effective"]["resolved_agent_mcp_server_denylist"]
    assert len(eff) == 12
    assert eff[0] == "frag-0"
