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
    ),
    ToolManifestEntry(
        "workspace_graph_reltypes",
        "graph",
        ("workspace", "graph", "neo4j", "relationship", "rel_type", "edge", "schema"),
        "low",
        "workspace",
        "retrieval_agent",
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
    ),
    ToolManifestEntry(
        "find_works",
        "catalog",
        ("workspace", "search", "paper", "title", "entity", "fulltext", "work"),
        "low",
        "corpus",
        "retrieval_agent",
        False,
    ),
    ToolManifestEntry(
        "paper_quote_search",
        "evidence",
        ("quote", "chunk", "passage", "semantic", "evidence", "tradeoff", "accuracy", "speed"),
        "medium",
        "corpus",
        "retrieval_agent",
        False,
    ),
    ToolManifestEntry(
        "format_bibliography_gost",
        "bibliography",
        ("bibliography", "gost", "references", "export"),
        "low",
        "workspace",
        "retrieval_agent",
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
    ),
    ToolManifestEntry(
        "cypher_query",
        "graph",
        ("cypher", "graph", "advanced", "neo4j"),
        "high",
        "graph",
        "graph_agent",
        False,
    ),
    ToolManifestEntry(
        "edge_search",
        "graph",
        ("edge", "relation", "graph"),
        "medium",
        "graph",
        "graph_agent",
        False,
    ),
    ToolManifestEntry(
        "final_answer",
        "writer",
        ("answer", "final"),
        "low",
        "writer",
        "writer_agent",
        False,
    ),
)


def manifest_by_name() -> dict[str, ToolManifestEntry]:
    """Return tool manifest entries keyed by tool name."""
    return {e.name: e for e in TOOL_MANIFEST}
