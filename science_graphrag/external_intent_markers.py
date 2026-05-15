"""External research intent markers (web + arXiv).

Placed at the ``science_graphrag`` package root (not under ``agent/``) so
``request_turn_policy`` / ``graph.state`` can import it without triggering
``science_graphrag.agent`` package initialization (which eagerly imports runtime).
"""

from __future__ import annotations

# Explicit internet / web research intent (retrieval must keep web_search / web_fetch).
WEB_RESEARCH_MARKERS_RU: tuple[str, ...] = (
    "интернет",
    "в интернете",
    "веб",
    "что говорят",
    "сейчас обсуждают",
)
WEB_RESEARCH_MARKERS_EN: tuple[str, ...] = (
    "web",
    "internet",
    "online",
    "current discussion",
    "what are people saying",
)

WEB_FOLLOWUP_INTENT_MARKERS: tuple[str, ...] = tuple(
    dict.fromkeys((*WEB_RESEARCH_MARKERS_RU, *WEB_RESEARCH_MARKERS_EN))
)

ARXIV_MARKERS: tuple[str, ...] = (
    "arxiv",
    "arxiv.org",
    "pre-print",
    "preprint",
    "прелпринт",
    "препринт",
)

# OA / Unpaywall-by-DOI intent (shortlist + strict_deferred core_exempt for ``unpaywall_lookup``).
UNPAYWALL_LOOKUP_MARKERS: tuple[str, ...] = (
    "unpaywall",
    "open-access",
    "open access url",
    "oa pdf",
    "legal open access",
    "открытый доступ",
    "открытая версия статьи",
)

__all__ = [
    "ARXIV_MARKERS",
    "UNPAYWALL_LOOKUP_MARKERS",
    "WEB_FOLLOWUP_INTENT_MARKERS",
    "WEB_RESEARCH_MARKERS_EN",
    "WEB_RESEARCH_MARKERS_RU",
]
