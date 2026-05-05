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
