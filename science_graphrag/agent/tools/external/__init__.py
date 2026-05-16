"""External research HTTP tools (Crossref, arXiv, OA lookup, …).

Assembled in one place so :func:`build_retrieval_tools` does not grow a flat
list of unrelated ``build_*`` imports. See ADR 030.
"""

from __future__ import annotations

from typing import Any

from science_graphrag.agent.tools.arxiv_tools import build_arxiv_tools
from science_graphrag.agent.tools.external.openalex_works_search_tools import (
    build_openalex_works_search_tools,
)
from science_graphrag.agent.tools.external.pdf_read_tools import build_pdf_read_tools
from science_graphrag.agent.tools.external.semantic_scholar_tools import (
    build_semantic_scholar_tools,
)
from science_graphrag.agent.tools.external.unpaywall_tools import build_unpaywall_tools
from science_graphrag.agent.tools.web_research_tools import (
    build_crossref_web_search_tools,
    build_official_web_lookup_tools,
    build_web_fetch_tools,
)
from science_graphrag.config import Settings


def build_external_research_tools(*, settings: Settings) -> list[Any]:
    """Return all LangChain tools that hit external scholarly HTTP APIs."""
    out: list[Any] = []
    out.extend(build_official_web_lookup_tools(settings=settings))
    out.extend(build_web_fetch_tools(settings=settings))
    if bool(getattr(settings, "external_research_source_crossref_enabled", True)):
        out.extend(build_crossref_web_search_tools(settings=settings))
    if bool(getattr(settings, "external_research_source_arxiv_enabled", True)):
        out.extend(build_arxiv_tools(settings=settings))
    if settings.agent_unpaywall_oa_tool_enabled and bool(
        getattr(settings, "external_research_source_unpaywall_enabled", True)
    ):
        out.extend(build_unpaywall_tools(settings=settings))
    if bool(getattr(settings, "external_research_source_openalex_enabled", True)):
        out.extend(build_openalex_works_search_tools(settings))
    if bool(getattr(settings, "external_research_source_semantic_scholar_enabled", True)):
        out.extend(build_semantic_scholar_tools(settings))
    if bool(getattr(settings, "agent_pdf_read_tool_enabled", True)):
        out.extend(build_pdf_read_tools(settings=settings))
    return out


__all__ = ["build_external_research_tools"]
