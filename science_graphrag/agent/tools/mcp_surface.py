"""MCP-style tool surface (feature-gated HTTP JSON-RPC seam).

When ``agent_mcp_http_base_url`` is unset, tools return typed ``mcp_unconfigured`` payloads
instead of pulling in a full MCP manager runtime.
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx
from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from science_graphrag.config import Settings


def _mcp_audit_hint(
    *,
    phase: str,
    server: str | None,
    tool: str | None = None,
    resource_uri: str | None = None,
    auth_status: str | None = None,
    ok: bool | None = None,
    deny_reason: str | None = None,
) -> dict[str, Any]:
    h: dict[str, Any] = {
        "type": "mcp_audit",
        "phase": phase,
        "server": server,
        "auth_status": auth_status or "unknown",
    }
    if tool is not None:
        h["tool"] = tool
    if resource_uri is not None:
        h["resource_uri"] = resource_uri
    if ok is not None:
        h["ok"] = bool(ok)
    if deny_reason:
        h["deny_reason"] = deny_reason
    return h


def _server_denied(settings: Settings, server: str) -> str | None:
    s = (server or "").strip()
    if not s:
        return "empty_server"
    for frag in settings.agent_mcp_server_denylist or []:
        f = str(frag or "").strip()
        if f and f in s:
            return f"denylist_hit:{f}"
    return None


def _json_rpc(url: str, *, method: str, params: dict[str, Any], timeout: float) -> dict[str, Any]:
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": method,
        "params": params,
    }
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        body = resp.json()
    if not isinstance(body, dict):
        return {"ok": False, "error": "mcp_invalid_response", "detail": "non_object_json"}
    if body.get("error"):
        return {"ok": False, "error": "mcp_rpc_error", "detail": body.get("error")}
    return {"ok": True, "result": body.get("result")}


def _gate_common(settings: Settings, server: str) -> dict[str, Any] | None:
    if not settings.agent_mcp_tools_enabled:
        return {
            "ok": False,
            "error": "disabled",
            "server": server,
            "sse_hint": _mcp_audit_hint(
                phase="gate", server=server, ok=False, deny_reason="feature_disabled"
            ),
        }
    deny = _server_denied(settings, server)
    if deny:
        return {
            "ok": False,
            "error": "permission_denied",
            "reason": deny,
            "server": server,
            "sse_hint": _mcp_audit_hint(
                phase="deny", server=server, ok=False, deny_reason=deny
            ),
        }
    base = (settings.agent_mcp_http_base_url or "").strip()
    if not base:
        return {
            "ok": False,
            "error": "mcp_unconfigured",
            "server": server,
            "sse_hint": _mcp_audit_hint(
                phase="unconfigured", server=server, ok=False, deny_reason="missing_base_url"
            ),
        }
    return None


class McpCallArgs(BaseModel):
    server: str = Field(..., description="Logical MCP server identifier.")
    tool: str = Field(..., description="Tool name to invoke on the server.")
    arguments: dict[str, Any] = Field(default_factory=dict, description="JSON arguments object.")


class McpListResourcesArgs(BaseModel):
    server: str = Field(..., description="Logical MCP server identifier.")


class McpFetchResourceArgs(BaseModel):
    server: str = Field(..., description="Logical MCP server identifier.")
    resource_uri: str = Field(..., description="Resource URI to fetch.")


class McpAuthArgs(BaseModel):
    server: str = Field(..., description="Logical MCP server identifier.")
    reason: str | None = Field(default=None, description="Optional client context for auth handoff.")


def build_mcp_surface_tools(settings: Settings) -> list[BaseTool]:
    """Build LangChain tools for MCP surface (may return empty when globally disabled)."""
    if not settings.agent_mcp_tools_enabled:
        return []

    @tool("call_mcp_tool", args_schema=McpCallArgs)
    def call_mcp_tool(server: str, tool: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """Invoke an MCP tool via configured HTTP JSON-RPC adapter."""
        args = dict(arguments or {})
        gated = _gate_common(settings, server)
        if gated:
            return gated
        base = (settings.agent_mcp_http_base_url or "").strip()
        try:
            out = _json_rpc(
                base,
                method="tools/call",
                params={"server": server, "name": tool, "arguments": args},
                timeout=float(settings.agent_mcp_request_timeout_seconds),
            )
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "error": "mcp_transport_error",
                "server": server,
                "tool": tool,
                "detail": str(exc)[:400],
                "sse_hint": _mcp_audit_hint(
                    phase="call",
                    server=server,
                    tool=tool,
                    ok=False,
                    deny_reason="transport",
                ),
            }
        hint = _mcp_audit_hint(phase="call", server=server, tool=tool, ok=bool(out.get("ok")))
        return {**out, "server": server, "tool": tool, "sse_hint": hint}

    @tool("list_mcp_resources", args_schema=McpListResourcesArgs)
    def list_mcp_resources(server: str) -> dict[str, Any]:
        """List MCP resources for a server."""
        gated = _gate_common(settings, server)
        if gated:
            return gated
        base = (settings.agent_mcp_http_base_url or "").strip()
        try:
            out = _json_rpc(
                base,
                method="resources/list",
                params={"server": server},
                timeout=float(settings.agent_mcp_request_timeout_seconds),
            )
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "error": "mcp_transport_error",
                "server": server,
                "detail": str(exc)[:400],
                "sse_hint": _mcp_audit_hint(phase="list_resources", server=server, ok=False),
            }
        return {
            **out,
            "server": server,
            "sse_hint": _mcp_audit_hint(phase="list_resources", server=server, ok=bool(out.get("ok"))),
        }

    @tool("fetch_mcp_resource", args_schema=McpFetchResourceArgs)
    def fetch_mcp_resource(server: str, resource_uri: str) -> dict[str, Any]:
        """Fetch a single MCP resource by URI."""
        gated = _gate_common(settings, server)
        if gated:
            return gated
        base = (settings.agent_mcp_http_base_url or "").strip()
        try:
            out = _json_rpc(
                base,
                method="resources/read",
                params={"server": server, "uri": resource_uri},
                timeout=float(settings.agent_mcp_request_timeout_seconds),
            )
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "error": "mcp_transport_error",
                "server": server,
                "resource_uri": resource_uri,
                "detail": str(exc)[:400],
                "sse_hint": _mcp_audit_hint(
                    phase="fetch_resource",
                    server=server,
                    resource_uri=resource_uri,
                    ok=False,
                ),
            }
        return {
            **out,
            "server": server,
            "resource_uri": resource_uri,
            "sse_hint": _mcp_audit_hint(
                phase="fetch_resource",
                server=server,
                resource_uri=resource_uri,
                ok=bool(out.get("ok")),
            ),
        }

    @tool("mcp_auth", args_schema=McpAuthArgs)
    def mcp_auth(server: str, reason: str | None = None) -> dict[str, Any]:
        """Interactive auth handoff marker (does not perform OAuth itself)."""
        gated = _gate_common(settings, server)
        if gated and gated.get("error") == "disabled":
            return gated
        deny = _server_denied(settings, server)
        if deny:
            return {
                "ok": False,
                "error": "permission_denied",
                "reason": deny,
                "server": server,
                "sse_hint": _mcp_audit_hint(
                    phase="auth", server=server, auth_status="denied", ok=False, deny_reason=deny
                ),
            }
        return {
            "ok": True,
            "auth_status": "delegation_required",
            "server": server,
            "reason": (reason or "").strip() or None,
            "sse_hint": _mcp_audit_hint(
                phase="auth",
                server=server,
                auth_status="delegation_required",
                ok=True,
            ),
        }

    return [call_mcp_tool, list_mcp_resources, fetch_mcp_resource, mcp_auth]
