"""Shared validators for external web research live smoke (importable from tests)."""

from __future__ import annotations

from typing import Any

from science_graphrag.agent.web_evidence_policy import (
    classify_source_tier,
    detect_unsupported_negative_official_claim,
)


def tool_names_from_trace(trace: list[dict[str, Any]]) -> list[str]:
    return [str(x.get("tool") or "") for x in trace if isinstance(x, dict)]


def citation_urls(citations: list[Any]) -> list[str]:
    out: list[str] = []
    for c in citations:
        if isinstance(c, dict):
            url = str(c.get("url") or "").strip()
            if url:
                out.append(url)
    return out


def evaluate_external_web_research_case(data: dict[str, Any]) -> dict[str, Any]:
    """Score one ``/v2/agent/query`` JSON body for web evidence quality gates."""
    answer = str(data.get("answer") or "")
    trace = data.get("tool_trace") or []
    citations = data.get("citations") or []
    tools = tool_names_from_trace(trace if isinstance(trace, list) else [])
    urls = citation_urls(citations if isinstance(citations, list) else [])

    official_urls = [u for u in urls if classify_source_tier(u) == "official"]
    scholarly_only = (
        urls
        and not official_urls
        and all(classify_source_tier(u) in {"scholarly", "metadata_only"} for u in urls)
    )

    issues: list[str] = []
    if "official_web_lookup" not in tools and not official_urls:
        issues.append("missing_official_web_lookup_or_official_citation")
    if scholarly_only:
        issues.append("citations_scholarly_metadata_only")
    if detect_unsupported_negative_official_claim(answer):
        issues.append("unsupported_negative_official_claim")

    return {
        "ok": not issues,
        "issues": issues,
        "tools": tools,
        "citation_urls": urls,
        "official_citation_urls": official_urls,
        "answer_len": len(answer.strip()),
        "phoenix_trace_id": data.get("phoenix_trace_id"),
    }


def phoenix_has_official_lookup_span(span_names: list[str]) -> bool:
    for name in span_names:
        text = str(name or "")
        if text in {"official_web_lookup", "tool.official_web_lookup"}:
            return True
        if "official_web_lookup" in text:
            return True
    return False
