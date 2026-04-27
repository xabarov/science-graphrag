"""Research chat response envelope (Wave A — CH1)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from science_graphrag.agent.trace import ToolCallTrace

if TYPE_CHECKING:
    from science_graphrag.agent.graph.state import AgentState

ANSWER_CLASSES = frozenset(
    {
        "inventory",
        "fact_lookup",
        "grounded_explanation",
        "relation_tracing",
        "quote_extraction",
        "ideation",
        "bibliography_export",
        "synthesis",
        "chat",
        "clarification",
    }
)


def _last_user_question(state: AgentState | dict[str, Any]) -> str:
    from langchain_core.messages import HumanMessage

    meta = state.get("metadata") or {}
    raw = meta.get("raw_user_question")
    if isinstance(raw, str) and raw.strip():
        return raw
    for msg in reversed(list(state.get("messages") or [])):
        if isinstance(msg, HumanMessage):
            return str(msg.content or "")
    return ""


def heuristic_answer_class(question: str, hint: str | None) -> str:
    if hint and hint in ANSWER_CLASSES:
        return hint
    q = (question or "").lower()
    if any(x in q for x in ("гост", "gost", "bibliograph", "список литературы", "literature list")):
        return "bibliography_export"
    if any(x in q for x in ("цитат", "quote", "passage", "snippet", "где написано")):
        return "quote_extraction"
    if any(
        x in q
        for x in (
            "how many",
            "сколько",
            "список стат",
            "стать",
            "работ в",
            "работ в области",
            "papers in",
            "works in workspace",
        )
    ):
        return "inventory"
    if any(x in q for x in ("связ", "path", "cites", "cypher", "graph", "entity")):
        return "relation_tracing"
    if any(x in q for x in ("who authored", "автор", "authors of")):
        return "fact_lookup"
    return "grounded_explanation"


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
    """Treat GOST-shaped blocks as typed even when entries are empty or deferred."""
    if bib.get("entries"):
        return True
    if str(bib.get("format") or "").strip().lower() == "gost":
        return True
    lines = bib.get("lines")
    return isinstance(lines, list) and bool(lines)


def collect_typed_payloads(state: AgentState | dict[str, Any]) -> dict[str, Any]:
    """Scan specialist tool JSON payloads for typed blocks."""
    inventory: dict[str, Any] = {}
    quote_candidates: list[dict[str, Any]] = []
    bibliography: dict[str, Any] | None = None
    relation_trace: dict[str, Any] = {}
    specialist_results = state.get("specialist_results") or {}
    for _spec, payloads in specialist_results.items():
        for payload in payloads or []:
            if not isinstance(payload, dict):
                continue
            inv = payload.get("inventory")
            if isinstance(inv, dict):
                _merge_inventory(inventory, inv)
            qc = payload.get("quote_candidates")
            if isinstance(qc, list):
                quote_candidates.extend(qc)
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
        out["quote_candidates"] = quote_candidates[:50]
    if bibliography:
        out["bibliography"] = bibliography
    if relation_trace:
        out["relation_trace"] = relation_trace
    return out


def infer_class_from_trace(tool_names: set[str]) -> str | None:
    if "format_bibliography_gost" in tool_names:
        return "bibliography_export"
    if "paper_quote_search" in tool_names:
        return "quote_extraction"
    # Relation tracing has higher precedence than inventory/fact_lookup when graph tools are present.
    if {"entity_search", "edge_search", "cypher_query"} & tool_names:
        return "relation_tracing"
    if {"workspace_overview", "workspace_list_papers", "paper_counts"} & tool_names:
        return "inventory"
    if "paper_authors" in tool_names or "paper_metadata" in tool_names:
        return "fact_lookup"
    return None


def _append_evidence_warnings(
    *,
    answer_class: str,
    citations: list[dict[str, Any]],
    tool_names: set[str],
    quote_candidates: list[dict[str, Any]],
    warnings: list[str],
) -> None:
    """Best-effort evidence sufficiency flags (B-5, aligned with spec)."""
    if answer_class == "quote_extraction" and not quote_candidates:
        warnings.append("no_quote_found")
    if len(citations) < 1 and answer_class in (
        "grounded_explanation",
        "synthesis",
        "ideation",
    ):
        warnings.append("weak_evidence")

    core = {
        t
        for t in tool_names
        if t
        not in (
            "session_init",
            "route_to_specialist",
            "final_answer",
        )
    }
    graph_tools = core & {"cypher_query", "entity_search", "edge_search"}
    vectorish = core & {
        "idea_search",
        "summarize_workspace",
        "paper_quote_search",
    }
    if graph_tools and not vectorish:
        if "graph_only" not in warnings:
            warnings.append("graph_only")
    if vectorish and not graph_tools and answer_class == "relation_tracing" and core:
        warnings.append("text_only")


def build_chat_envelope(
    *,
    state: AgentState | dict[str, Any],
    answer: str,
    citations: list[dict[str, Any]],
    tool_trace: list[ToolCallTrace],
    answer_class_hint: str | None = None,
) -> dict[str, Any]:
    """Build optional envelope fields for API v2."""
    question = _last_user_question(state)
    meta = state.get("metadata") or {}
    tp = meta.get("turn_policy") if isinstance(meta.get("turn_policy"), dict) else {}
    tool_policy = str(tp.get("tool_policy") or "allow_tools")
    names = {str(t.get("tool") or "") for t in tool_trace if isinstance(t, dict)}
    names.discard("")
    _meta_tools = frozenset(
        {"session_init", "route_to_specialist", "coordinator_gate", "final_answer"}
    )
    core_tools = {n for n in names if n and n not in _meta_tools}
    from_trace = infer_class_from_trace(names)
    if tool_policy in {"no_tools", "clarify"}:
        suggested = str(tp.get("suggested_answer_class") or "chat")
        answer_class = suggested if suggested in ANSWER_CLASSES else "chat"
        typed: dict[str, Any] = {}
    else:
        answer_class = from_trace or heuristic_answer_class(question, answer_class_hint)
        typed = collect_typed_payloads(state)
    answer_stripped = (answer or "").strip()
    if not answer_stripped:
        product_path = "empty"
    elif core_tools:
        product_path = "tool_assisted"
    else:
        product_path = "direct"
    product_markers: list[str] = []
    if product_path == "tool_assisted":
        product_markers.append("answered_with_tools")
    elif product_path == "direct" and answer_stripped:
        product_markers.append("answered_directly")
    warnings: list[str] = []
    if not (state.get("workspace_id") or "").strip():
        warnings.append("no_workspace")
    quote_cands = list(typed.get("quote_candidates") or [])
    _append_evidence_warnings(
        answer_class=answer_class,
        citations=citations,
        tool_names=names,
        quote_candidates=quote_cands,
        warnings=warnings,
    )
    bib_obj = typed.get("bibliography")
    if isinstance(bib_obj, dict):
        for w in bib_obj.get("warnings") or []:
            if isinstance(w, str) and w.strip() and w not in warnings:
                warnings.append(w.strip())
        if bib_obj.get("filtered_work_ids") and "some_work_ids_filtered" not in warnings:
            warnings.append("some_work_ids_filtered")
    if not answer_stripped:
        warnings.append("no_final_answer")
    if (
        answer_stripped
        and not citations
        and answer_class
        in (
            "grounded_explanation",
            "synthesis",
            "relation_tracing",
            "quote_extraction",
            "ideation",
        )
        and product_path == "tool_assisted"
    ):
        warnings.append("no_citations")
    if "weak_evidence" in warnings and "insufficient_evidence" not in warnings:
        warnings.append("insufficient_evidence")
    evidence_parts: list[str] = []
    if citations:
        evidence_parts.append(f"{len(citations)} citation(s)")
    elif (answer or "").strip():
        evidence_parts.append("assistant reply (no citations)")
    if tool_trace:
        evidence_parts.append(f"{len(tool_trace)} trace step(s)")
    evidence_summary = ", ".join(evidence_parts) if evidence_parts else None
    out: dict[str, Any] = {
        "answer_class": answer_class,
        "evidence_summary": evidence_summary,
        "warnings": list(dict.fromkeys(warnings)),
        "product_path": product_path,
        "product_markers": list(dict.fromkeys(product_markers)),
    }
    out.update(typed)
    return out
