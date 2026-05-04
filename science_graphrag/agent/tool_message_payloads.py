"""Extract typed envelope fragments from ``ToolMessage`` JSON (single-agent ReAct path).

``specialist_results`` is populated only in supervisor subgraphs; research single-agent runs
store evidence solely in message history — reuse the same keys as ``collect_typed_payloads``.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import ToolMessage

from science_graphrag.agent.tool_call_normalization import normalize_tool_call_name


def _merge_inventory(acc: dict[str, Any], fragment: dict[str, Any]) -> None:
    if not fragment:
        return
    for key, val in fragment.items():
        if val is None:
            continue
        if key not in acc:
            acc[key] = val
            continue
        if isinstance(acc[key], list) and isinstance(val, list):
            acc[key] = acc[key] + val
        elif isinstance(acc[key], dict) and isinstance(val, dict):
            acc[key].update(val)
        else:
            acc[key] = val


def _bibliography_payload_acceptable(bib: dict[str, Any]) -> bool:
    if bib.get("entries"):
        return True
    if str(bib.get("format") or "").strip().lower() == "gost":
        return True
    lines = bib.get("lines")
    return isinstance(lines, list) and bool(lines)


def typed_payloads_from_tool_messages(
    messages: list[Any],
    *,
    quote_candidate_cap: int = 50,
) -> dict[str, Any]:
    """Merge ``inventory``, ``quote_candidates``, ``bibliography``, ``relation_trace`` from tools."""

    inventory: dict[str, Any] = {}
    quote_candidates: list[dict[str, Any]] = []
    bibliography: dict[str, Any] | None = None
    relation_trace: dict[str, Any] = {}

    for msg in messages:
        if not isinstance(msg, ToolMessage):
            continue
        name = normalize_tool_call_name(str(getattr(msg, "name", "") or ""))
        raw = str(msg.content or "").strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue

        inv = payload.get("inventory")
        if isinstance(inv, dict):
            _merge_inventory(inventory, inv)
        qc = payload.get("quote_candidates")
        if isinstance(qc, list) and name == "paper_quote_search":
            quote_candidates.extend([x for x in qc if isinstance(x, dict)])
        bib = payload.get("bibliography")
        if isinstance(bib, dict) and _bibliography_payload_acceptable(bib):
            bibliography = bib
        rt = payload.get("relation_trace")
        if isinstance(rt, dict) and rt:
            relation_trace.update(rt)

    out: dict[str, Any] = {}
    if inventory:
        out["inventory"] = inventory
    if quote_candidates:
        out["quote_candidates"] = quote_candidates[:quote_candidate_cap]
    if bibliography:
        out["bibliography"] = bibliography
    if relation_trace:
        out["relation_trace"] = relation_trace
    return out
