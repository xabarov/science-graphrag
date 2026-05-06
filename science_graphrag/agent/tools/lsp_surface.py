"""Bounded read-only ``lsp_tool`` (stdio JSON-RPC seam).

Requires ``agent_lsp_server_argv`` (non-empty). Without it, tools return ``lsp_unconfigured``.
"""

from __future__ import annotations

import io
import json
import select
import subprocess
import time
import uuid
from typing import Any, TextIO

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field, field_validator

from science_graphrag.config import Settings


def _lsp_audit_hint(
    *,
    operation: str,
    ok: bool | None = None,
    budget_items: int | None = None,
    timeout_hit: bool | None = None,
    degraded: bool | None = None,
) -> dict[str, Any]:
    h: dict[str, Any] = {
        "type": "lsp_audit",
        "operation": operation,
    }
    if ok is not None:
        h["ok"] = bool(ok)
    if budget_items is not None:
        h["payload_budget_items"] = int(budget_items)
    if timeout_hit is not None:
        h["timeout_hit"] = bool(timeout_hit)
    if degraded is not None:
        h["degraded"] = bool(degraded)
    return h


class LspToolArgs(BaseModel):
    operation: str = Field(
        ...,
        description="One of: workspace_symbol, references, definition.",
    )
    uri: str = Field(default="", description="textDocument uri (file://...) when required.")
    query: str = Field(default="", description="Query string for workspace_symbol.")
    line: int = Field(default=0, ge=0, description="0-based line for references/definition.")
    character: int = Field(default=0, ge=0, description="0-based utf-16 offset for references/definition.")

    @field_validator("operation", mode="before")
    @classmethod
    def _norm_op(cls, v: object) -> str:
        return str(v or "").strip().lower()


def _read_json_rpc_line(
    stdout: TextIO,
    *,
    expect_id: str,
    deadline: float,
) -> dict[str, Any] | None:
    while time.monotonic() < deadline:
        remaining = max(0.0, deadline - time.monotonic())
        if remaining <= 0:
            break
        rlist, _, _ = select.select([stdout], [], [], min(0.25, remaining))
        if not rlist:
            continue
        line = stdout.readline()
        if not line:
            time.sleep(0.02)
            continue
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(msg, dict):
            continue
        if msg.get("id") == expect_id:
            return msg
    return None


def _encode_lsp_message(msg: dict[str, Any]) -> str:
    body = json.dumps(msg, ensure_ascii=False)
    return f"Content-Length: {len(body.encode('utf-8'))}\r\n\r\n{body}"


def _read_lsp_message(
    stdout: TextIO,
    *,
    deadline: float,
) -> dict[str, Any] | None:
    """Read one stdio-framed LSP message; fallback to NDJSON for local shims/tests."""

    def _wait_ready() -> bool:
        remaining = max(0.0, deadline - time.monotonic())
        if remaining <= 0:
            return False
        try:
            rlist, _, _ = select.select([stdout], [], [], min(0.25, remaining))
        except (OSError, ValueError, io.UnsupportedOperation):
            return True
        return bool(rlist)

    header_lines: list[str] = []
    while time.monotonic() < deadline:
        if not _wait_ready():
            continue
        line = stdout.readline()
        if not line:
            time.sleep(0.02)
            continue
        if not header_lines and line.lstrip().startswith("{"):
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            return payload if isinstance(payload, dict) else None
        stripped = line.rstrip("\r\n")
        if stripped:
            header_lines.append(stripped)
            continue
        content_length: int | None = None
        for hdr in header_lines:
            if ":" not in hdr:
                continue
            key, value = hdr.split(":", 1)
            if key.strip().lower() == "content-length":
                try:
                    content_length = int(value.strip())
                except ValueError:
                    return None
                break
        if content_length is None or content_length < 0:
            return None
        chunks: list[str] = []
        remaining_bytes = content_length
        while remaining_bytes > 0 and time.monotonic() < deadline:
            if not _wait_ready():
                continue
            chunk = stdout.read(remaining_bytes)
            if not chunk:
                time.sleep(0.02)
                continue
            chunks.append(chunk)
            remaining_bytes -= len(chunk.encode("utf-8"))
        if remaining_bytes > 0:
            return None
        try:
            payload = json.loads("".join(chunks))
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None
    return None


def _lsp_stdio_exchange(
    argv: list[str],
    outbound: list[dict[str, Any]],
    *,
    per_request_timeout: float,
) -> tuple[list[dict[str, Any] | None], str | None]:
    """Send JSON-RPC messages; wait for responses only for outbound objects that include ``id``."""
    proc = subprocess.Popen(  # noqa: S603 - argv from admin settings only
        argv,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    assert proc.stdin is not None and proc.stdout is not None
    out: list[dict[str, Any] | None] = []
    err: str | None = None
    try:
        for msg in outbound:
            proc.stdin.write(_encode_lsp_message(msg))
            proc.stdin.flush()
            rid = msg.get("id")
            if rid is None:
                continue
            rid_s = str(rid)
            deadline = time.monotonic() + float(per_request_timeout)
            resp: dict[str, Any] | None = None
            while time.monotonic() < deadline:
                candidate = _read_lsp_message(proc.stdout, deadline=deadline)
                if candidate is None:
                    break
                if candidate.get("id") != rid_s:
                    continue
                resp = candidate
                break
            out.append(resp)
            if resp is None:
                err = "lsp_response_timeout"
                break
            if resp.get("error"):
                err = json.dumps(resp.get("error"), ensure_ascii=False)[:400]
                break
    except Exception as exc:  # noqa: BLE001
        err = str(exc)[:400]
    finally:
        try:
            proc.terminate()
        except ProcessLookupError:
            pass
        try:
            proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            proc.kill()
    return out, err


def _decode_lsp_messages_from_text(raw: str) -> list[dict[str, Any]]:
    """Test helper: decode one or more framed LSP messages from text."""
    buf = io.StringIO(raw)
    out: list[dict[str, Any]] = []
    while True:
        msg = _read_lsp_message(buf, deadline=time.monotonic() + 0.01)
        if msg is None:
            break
        out.append(msg)
    return out


def build_lsp_tool(settings: Settings) -> list[BaseTool]:
    if not settings.agent_lsp_tool_enabled:
        return []

    @tool("lsp_tool", args_schema=LspToolArgs)
    def lsp_tool(  # pylint: disable=too-many-locals
        operation: str,
        uri: str = "",
        query: str = "",
        line: int = 0,
        character: int = 0,
    ) -> dict[str, Any]:
        """Read-only LSP helper: workspace_symbol / references / go-to-definition (stdio)."""
        op = (operation or "").strip().lower()
        argv = [str(x) for x in (settings.agent_lsp_server_argv or []) if str(x).strip()]
        if not argv:
            return {
                "ok": False,
                "error": "lsp_unconfigured",
                "operation": op,
                "sse_hint": _lsp_audit_hint(operation=op, ok=False, degraded=True),
            }
        if op not in {"workspace_symbol", "references", "definition"}:
            return {
                "ok": False,
                "error": "unsupported_operation",
                "operation": op,
                "sse_hint": _lsp_audit_hint(operation=op, ok=False),
            }
        timeout = float(settings.agent_lsp_request_timeout_seconds)
        budget = int(settings.agent_lsp_max_result_items)
        root_uri = "file:///tmp"
        init_id = str(uuid.uuid4())
        sym_id = str(uuid.uuid4())
        outbound: list[dict[str, Any]] = [
            {
                "jsonrpc": "2.0",
                "id": init_id,
                "method": "initialize",
                "params": {
                    "processId": None,
                    "rootUri": root_uri,
                    "capabilities": {},
                    "workspaceFolders": None,
                },
            },
            {"jsonrpc": "2.0", "method": "initialized", "params": {}},
        ]
        if op == "workspace_symbol":
            outbound.append(
                {
                    "jsonrpc": "2.0",
                    "id": sym_id,
                    "method": "workspace/symbol",
                    "params": {"query": (query or "")[:256]},
                }
            )
        elif op == "references":
            if not (uri or "").strip():
                return {
                    "ok": False,
                    "error": "missing_uri",
                    "operation": op,
                    "sse_hint": _lsp_audit_hint(operation=op, ok=False),
                }
            outbound.append(
                {
                    "jsonrpc": "2.0",
                    "id": sym_id,
                    "method": "textDocument/references",
                    "params": {
                        "textDocument": {"uri": uri.strip()},
                        "position": {"line": int(line), "character": int(character)},
                        "context": {"includeDeclaration": True},
                    },
                }
            )
        else:  # definition
            if not (uri or "").strip():
                return {
                    "ok": False,
                    "error": "missing_uri",
                    "operation": op,
                    "sse_hint": _lsp_audit_hint(operation=op, ok=False),
                }
            outbound.append(
                {
                    "jsonrpc": "2.0",
                    "id": sym_id,
                    "method": "textDocument/definition",
                    "params": {
                        "textDocument": {"uri": uri.strip()},
                        "position": {"line": int(line), "character": int(character)},
                    },
                }
            )

        responses, err = _lsp_stdio_exchange(argv, outbound, per_request_timeout=timeout)
        if err:
            return {
                "ok": False,
                "error": err,
                "operation": op,
                "responses_seen": len(responses),
                "sse_hint": _lsp_audit_hint(
                    operation=op, ok=False, timeout_hit="timeout" in err, degraded=True
                ),
            }
        last = responses[-1] if responses else None
        result = last.get("result") if isinstance(last, dict) else None
        items: list[Any] = []
        if isinstance(result, list):
            items = result[:budget]
        elif isinstance(result, dict):
            items = [result]
        truncated = isinstance(result, list) and len(result) > budget
        return {
            "ok": True,
            "operation": op,
            "items": items,
            "row_count": len(items),
            "truncated": bool(truncated),
            "sse_hint": _lsp_audit_hint(
                operation=op,
                ok=True,
                budget_items=budget,
                degraded=len(items) == 0,
            ),
        }

    return [lsp_tool]
