"""Static tool metadata for rule-based tool_search (Wave A — CH3)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SpecialistName = Literal["retrieval_agent", "graph_agent", "writer_agent"]


@dataclass(frozen=True)
class ToolManifestEntry:
    """Human- and machine-readable tool metadata."""

    name: str
    family: str
    tags: tuple[str, ...]
    risk: Literal["low", "medium", "high"]
    scope: Literal["workspace", "graph", "corpus", "writer"]
    specialist: SpecialistName | None
    requires_workspace: bool
    prompt_summary: str
    deferred_schema_ref: str
    #: When ``agent_tool_search_strict_deferred_activation_enabled``, bind shortlist drops this
    #: tool unless it was rule-scored, merged from message history, session carry-over, or is part
    #: of the retrieval core trio baseline (workspace_inspect / paper_profile / find_works).
    strict_deferred_requires_discovery: bool = False


# Names must match LangChain @tool function names.
TOOL_MANIFEST: tuple[ToolManifestEntry, ...] = (
    ToolManifestEntry(
        "workspace_inspect",
        "catalog",
        ("workspace", "inventory", "count", "list", "summary", "overview"),
        "low",
        "workspace",
        "retrieval_agent",
        True,
        "Workspace inventory and counts",
        "tool://workspace_inspect",
        False,
    ),
    ToolManifestEntry(
        "workspace_graph_reltypes",
        "graph",
        ("workspace", "graph", "neo4j", "relationship", "rel_type", "edge", "schema"),
        "low",
        "workspace",
        "retrieval_agent",
        True,
        "Workspace graph relationship types/schema",
        "tool://workspace_graph_reltypes",
        True,
    ),
    ToolManifestEntry(
        "paper_profile",
        "catalog",
        ("paper", "metadata", "doi", "year", "authors", "authorship"),
        "low",
        "workspace",
        "retrieval_agent",
        False,
        "Work metadata by work_id",
        "tool://paper_profile",
    ),
    ToolManifestEntry(
        "find_works",
        "catalog",
        ("workspace", "search", "paper", "title", "entity", "fulltext", "work"),
        "low",
        "corpus",
        "retrieval_agent",
        False,
        "Find works by text/title query",
        "tool://find_works",
    ),
    ToolManifestEntry(
        "paper_quote_search",
        "evidence",
        ("quote", "chunk", "passage", "semantic", "evidence", "tradeoff", "accuracy", "speed"),
        "medium",
        "corpus",
        "retrieval_agent",
        False,
        "Semantic quote/passage retrieval",
        "tool://paper_quote_search",
        True,
    ),
    ToolManifestEntry(
        "format_bibliography_gost",
        "bibliography",
        ("bibliography", "gost", "references", "export"),
        "low",
        "workspace",
        "retrieval_agent",
        True,
        "Format bibliography in GOST",
        "tool://format_bibliography_gost",
        True,
    ),
    ToolManifestEntry(
        "idea_search",
        "retrieval",
        ("semantic", "chunk", "search", "idea"),
        "medium",
        "corpus",
        "retrieval_agent",
        False,
        "Semantic discovery across chunks",
        "tool://idea_search",
        True,
    ),
    ToolManifestEntry(
        "cypher_query",
        "graph",
        ("cypher", "graph", "advanced", "neo4j"),
        "high",
        "graph",
        "graph_agent",
        False,
        "Read-only Cypher graph queries",
        "tool://cypher_query",
        True,
    ),
    ToolManifestEntry(
        "edge_search",
        "graph",
        ("edge", "relation", "graph"),
        "medium",
        "graph",
        "graph_agent",
        False,
        "Edge neighborhood lookup",
        "tool://edge_search",
        True,
    ),
    ToolManifestEntry(
        "web_search",
        "external",
        ("web", "search", "doi", "literature", "arxiv", "paper", "external", "crossref"),
        "medium",
        "corpus",
        "retrieval_agent",
        False,
        "Academic web search (Crossref-backed)",
        "tool://web_search",
        True,
    ),
    ToolManifestEntry(
        "web_fetch",
        "external",
        ("web", "fetch", "url", "http", "https", "summary", "page"),
        "medium",
        "corpus",
        "retrieval_agent",
        False,
        "Fetch and summarize allowed scholarly URLs",
        "tool://web_fetch",
        True,
    ),
    ToolManifestEntry(
        "doi_resolver",
        "external",
        ("doi", "openalex", "metadata", "url", "resolve", "identifier"),
        "low",
        "corpus",
        "retrieval_agent",
        False,
        "Resolve DOI or DOI URL to metadata and optional workspace work id",
        "tool://doi_resolver",
        True,
    ),
    ToolManifestEntry(
        "final_answer",
        "writer",
        ("answer", "final"),
        "low",
        "writer",
        "writer_agent",
        False,
        "Structured final answer output",
        "tool://final_answer",
    ),
)


def manifest_by_name() -> dict[str, ToolManifestEntry]:
    """Return tool manifest entries keyed by tool name."""
    return {e.name: e for e in TOOL_MANIFEST}


def compact_catalog_lines(*, specialist: SpecialistName | None = None) -> list[str]:
    """Human-readable compact catalog lines for prompts/debug artifacts."""
    rows: list[str] = []
    for entry in TOOL_MANIFEST:
        if specialist is not None and entry.specialist not in (None, specialist):
            continue
        rows.append(f"{entry.name}: {entry.prompt_summary}")
    return rows
