"""Compare app ``tool_trace`` with optional Phoenix HTTP snapshot (best-effort)."""

from __future__ import annotations

from typing import Any


def _effective_payload_valid_and_kind(snap: dict[str, Any]) -> tuple[bool, str | None]:
    """Infer ``payload_valid`` / kind when older snapshots omit ``payload_valid``."""

    if "payload_valid" in snap:
        pk = snap.get("payload_kind")
        kind = pk if isinstance(pk, str) else None
        return bool(snap["payload_valid"]), kind
    if not snap.get("ok"):
        pk = snap.get("payload_kind")
        kind = pk if isinstance(pk, str) else None
        return False, kind
    from eval.chat_agent.phoenix_export import _classify_phoenix_json_payload

    valid, kind = _classify_phoenix_json_payload(snap.get("payload"))
    return valid, kind


def _collect_string_names(obj: Any, out: set[str]) -> None:
    if isinstance(obj, dict):
        name = obj.get("name")
        if isinstance(name, str) and name.strip():
            out.add(name.strip())
        for v in obj.values():
            _collect_string_names(v, out)
    elif isinstance(obj, list):
        for item in obj:
            _collect_string_names(item, out)


def _expected_tool_spans(tool_trace: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for step in tool_trace:
        if not isinstance(step, dict):
            continue
        raw = str(step.get("tool") or "").strip()
        if not raw or raw.startswith("route_") or raw in {"session_init", "coordinator_gate"}:
            continue
        names.append(f"tool.{raw}")
    return names


def _expected_retriever_spans(tool_trace: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for step in tool_trace:
        if not isinstance(step, dict):
            continue
        t = str(step.get("tool") or "").strip()
        if t in {"idea_search", "paper_quote_search"}:
            out.append(f"retrieval.qdrant.{t}")
    return out


def build_observability_trace_audit(
    *,
    tool_trace: list[dict[str, Any]],
    phoenix_http_snapshot: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return structured observability block for ``trace_audit.json``."""

    expected_tool_spans = _expected_tool_spans(tool_trace)
    expected_retriever_spans = _expected_retriever_spans(tool_trace)
    snap = phoenix_http_snapshot if isinstance(phoenix_http_snapshot, dict) else None

    base_out: dict[str, Any] = {
        "phoenix_fetch_ok": False,
        "phoenix_payload_kind": None,
        "phoenix_payload_valid": False,
        "observability_match_reliable": False,
        "expected_span_names": [*expected_tool_spans, *expected_retriever_spans],
        "span_names_seen": [],
        "span_gaps": [],
        "missing_tool_spans": [],
        "missing_retriever_spans": [],
        "missing_llm_token_attrs": None,
        "tool_trace_vs_phoenix_match": None,
        "observability_passed": True,
    }

    if not snap:
        return base_out

    base_out["phoenix_fetch_ok"] = bool(snap.get("ok"))
    eff_valid, inferred_kind = _effective_payload_valid_and_kind(snap)
    base_out["phoenix_payload_valid"] = eff_valid
    base_out["phoenix_payload_kind"] = snap.get("payload_kind") or inferred_kind

    if not snap.get("ok"):
        base_out["observability_match_reliable"] = False
        base_out["observability_passed"] = True
        return base_out

    if not eff_valid:
        base_out["observability_match_reliable"] = False
        base_out["observability_passed"] = True
        base_out["tool_trace_vs_phoenix_match"] = None
        return base_out

    payload = snap.get("payload")
    seen: set[str] = set()
    _collect_string_names(payload, seen)

    missing_tools = [n for n in expected_tool_spans if n not in seen]
    missing_ret = [n for n in expected_retriever_spans if n not in seen]
    span_gaps = [*missing_tools, *missing_ret]

    match_ok = not missing_tools and not missing_ret
    base_out["observability_match_reliable"] = True
    base_out["span_names_seen"] = sorted(seen)
    base_out["span_gaps"] = span_gaps
    base_out["missing_tool_spans"] = missing_tools
    base_out["missing_retriever_spans"] = missing_ret
    base_out["tool_trace_vs_phoenix_match"] = {"ok": match_ok, "missing": span_gaps}
    base_out["observability_passed"] = match_ok
    return base_out


__all__ = [
    "build_observability_trace_audit",
]
