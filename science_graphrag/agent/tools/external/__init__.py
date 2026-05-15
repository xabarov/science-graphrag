"""External research HTTP tools (Crossref, arXiv, OA lookup, …).

Assembled in one place so :func:`build_retrieval_tools` does not grow a flat
list of unrelated ``build_*`` imports. See ADR 030.
"""

from __future__ import annotations

from typing import Any

from science_graphrag.agent.tools.arxiv_tools import build_arxiv_tools
from science_graphrag.agent.tools.external.unpaywall_tools import build_unpaywall_tools
from science_graphrag.agent.tools.web_research_tools import build_web_research_tools
from science_graphrag.config import Settings


def build_external_research_tools(*, settings: Settings) -> list[Any]:
    """Return all LangChain tools that hit external scholarly HTTP APIs."""
    out: list[Any] = []
    out.extend(build_web_research_tools(settings=settings))
    out.extend(build_arxiv_tools(settings=settings))
    if settings.agent_unpaywall_oa_tool_enabled:
        out.extend(build_unpaywall_tools(settings=settings))
    return out


__all__ = ["build_external_research_tools"]
