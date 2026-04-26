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
        "workspace_overview",
        "catalog",
        ("workspace", "inventory", "count"),
        "low",
        "workspace",
        "retrieval_agent",
        True,
    ),
    ToolManifestEntry(
        "workspace_list_papers",
        "catalog",
        ("workspace", "papers", "inventory", "list"),
        "low",
        "workspace",
        "retrieval_agent",
        True,
    ),
    ToolManifestEntry(
        "paper_lookup",
        "catalog",
        ("workspace", "search", "paper", "title"),
        "low",
        "workspace",
        "retrieval_agent",
        True,
    ),
    ToolManifestEntry(
        "paper_metadata",
        "catalog",
        ("paper", "metadata", "doi", "year"),
        "low",
        "workspace",
        "retrieval_agent",
        False,
    ),
    ToolManifestEntry(
        "paper_authors",
        "catalog",
        ("paper", "authors", "authorship"),
        "low",
        "workspace",
        "retrieval_agent",
        False,
    ),
    ToolManifestEntry(
        "paper_counts",
        "catalog",
        ("workspace", "count", "how_many"),
        "low",
        "workspace",
        "retrieval_agent",
        True,
    ),
    ToolManifestEntry(
        "paper_quote_search",
        "evidence",
        ("quote", "chunk", "passage", "semantic", "evidence"),
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
        "summarize_workspace",
        "retrieval",
        ("workspace", "summary", "overview"),
        "low",
        "workspace",
        "retrieval_agent",
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
    ),
    ToolManifestEntry(
        "entity_search",
        "graph",
        ("entity", "graph", "lookup"),
        "medium",
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
    return {e.name: e for e in TOOL_MANIFEST}
