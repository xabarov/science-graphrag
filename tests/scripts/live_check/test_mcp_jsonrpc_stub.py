"""Unit tests for MCP JSON-RPC stub dispatcher."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts" / "live_check"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from mcp_jsonrpc_stub import dispatch_rpc  # pylint: disable=import-error, wrong-import-position


def test_dispatch_tools_list() -> None:
    out = dispatch_rpc({"id": "1", "method": "tools/list", "params": {"server": "smoke"}})
    assert out.get("error") is None
    result = out.get("result")
    assert isinstance(result, dict)
    assert result.get("server") == "smoke"
    assert isinstance(result.get("tools"), list)


def test_dispatch_tools_call() -> None:
    out = dispatch_rpc(
        {
            "id": 2,
            "method": "tools/call",
            "params": {"server": "smoke", "name": "ping", "arguments": {}},
        }
    )
    result = out.get("result")
    assert isinstance(result, dict)
    assert result.get("tool") == "ping"
    content = result.get("content")
    assert isinstance(content, list) and content[0].get("text") == "pong"


def test_dispatch_unknown_method() -> None:
    out = dispatch_rpc({"id": 3, "method": "nope", "params": {}})
    assert out.get("error") is not None
