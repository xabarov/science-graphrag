"""Single source of truth for prompt-derived routing features (Phase 2).

Replaces scattered substring/regex checks in
:mod:`science_graphrag.agent.coordination.deterministic` and
:mod:`science_graphrag.agent.graph.supervisor` with one extractor.

Routing rules (planner, supervisor) consume :class:`QuestionFeatures`,
**never** the raw user prompt. New acceptance variants therefore become a
new feature flag here + a planner rule, not a new branch in
``supervisor_node``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from science_graphrag.agent.coordination.deterministic import (
    _GRAPH_INTENT_HINTS,
    graph_intent_heuristic,
)
from science_graphrag.agent.web_evidence_policy import asks_for_official_product_research
from science_graphrag.external_intent_markers import (
    ARXIV_MARKERS,
    UNPAYWALL_LOOKUP_MARKERS,
    WEB_RESEARCH_MARKERS_EN,
    WEB_RESEARCH_MARKERS_RU,
)

QuestionLanguage = Literal["en", "ru", "mixed", "unknown"]


# ---------------------------------------------------------------------------
# Substring / regex marker tables (centralized)
# ---------------------------------------------------------------------------


# Catalog-compare prompts (workspace-scoped dual evidence). Mirrors
# ``_DUAL_EVIDENCE_CATALOG_COMPARE_MARKERS`` historically in supervisor.py.
_DUAL_EVIDENCE_COMPARE_MARKERS: tuple[str, ...] = (
    "compare evidence",
    "compare two",
    "two different",
    "different title keywords",
    "distinct work_ids",
    "disagree on any factual point",
)


# Simple title-resolution / catalog completion markers (find_works + paper_profile).
_CATALOG_RESOLUTION_MARKERS: tuple[str, ...] = (
    "titles mention",
    "pick one clear match",
    "clear match",
    "year and venue",
    "report year and venue",
)


_QUOTE_EVIDENCE_MARKERS: tuple[str, ...] = (
    "quote one short snippet",
    "quote one",
    "short snippet",
    "anchor-free",
    "anchor free",
)


_WORKSPACE_STATS_MARKERS: tuple[str, ...] = (
    "how many works",
    "how many papers",
    "works are in this workspace",
    "сколько",
    "mode=stats",
    "claim-related",
    "citation-related counts",
)


_BIBLIOGRAPHY_GOST_MARKERS: tuple[str, ...] = (
    "gost",
    "bibliograph",
    "список литературы",
)


_QUOTE_VERBATIM_MARKERS: tuple[str, ...] = (
    "quote",
    "snippet",
    "verbatim",
    "цитат",
)


_RU_LETTERS = re.compile(r"[а-яё]", re.IGNORECASE)
_EN_LETTERS = re.compile(r"[a-z]", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QuestionFeatures:
    """Typed view of the user prompt used by routing rules.

    All fields are derived deterministically from the raw question + workspace.
    Empty / missing fields are normalized to ``False`` / ``None``.
    """

    raw_question: str
    normalized_question: str
    has_workspace: bool
    language: QuestionLanguage

    asks_for_compare: bool = False
    asks_for_dual_evidence: bool = False
    asks_for_catalog_resolution: bool = False
    asks_for_workspace_stats: bool = False
    asks_for_quotes: bool = False
    asks_for_bibliography_gost: bool = False
    asks_for_anchor_free_quote: bool = False
    asks_for_relations: bool = False  # cited / paths / cypher / lineage
    asks_for_web_research: bool = False
    asks_for_official_product_research: bool = False
    asks_for_arxiv: bool = False
    asks_for_unpaywall: bool = False

    matched_markers: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        """Plain-dict view for state metadata caching (round-trip with ``from_dict``)."""
        return {
            "raw_question": self.raw_question,
            "normalized_question": self.normalized_question,
            "has_workspace": bool(self.has_workspace),
            "language": str(self.language),
            "asks_for_compare": bool(self.asks_for_compare),
            "asks_for_dual_evidence": bool(self.asks_for_dual_evidence),
            "asks_for_catalog_resolution": bool(self.asks_for_catalog_resolution),
            "asks_for_workspace_stats": bool(self.asks_for_workspace_stats),
            "asks_for_quotes": bool(self.asks_for_quotes),
            "asks_for_bibliography_gost": bool(self.asks_for_bibliography_gost),
            "asks_for_anchor_free_quote": bool(self.asks_for_anchor_free_quote),
            "asks_for_relations": bool(self.asks_for_relations),
            "asks_for_web_research": bool(self.asks_for_web_research),
            "asks_for_official_product_research": bool(self.asks_for_official_product_research),
            "asks_for_arxiv": bool(self.asks_for_arxiv),
            "asks_for_unpaywall": bool(self.asks_for_unpaywall),
            "matched_markers": list(self.matched_markers),
        }

    @classmethod
    def from_dict(cls, payload: Any) -> "QuestionFeatures | None":
        """Inverse of :meth:`to_dict`.

        Returns ``None`` if the payload is missing the minimum required fields,
        so callers can transparently fall back to recomputation.
        """
        if not isinstance(payload, dict):
            return None
        qn = payload.get("normalized_question")
        if not isinstance(qn, str) or not qn:
            return None
        lang_raw = str(payload.get("language") or "unknown")
        if lang_raw not in {"en", "ru", "mixed", "unknown"}:
            lang_raw = "unknown"
        markers_raw = payload.get("matched_markers")
        markers: tuple[str, ...]
        if isinstance(markers_raw, (list, tuple)):
            markers = tuple(str(m) for m in markers_raw if isinstance(m, str))
        else:
            markers = ()
        return cls(
            raw_question=str(payload.get("raw_question") or qn),
            normalized_question=qn,
            has_workspace=bool(payload.get("has_workspace")),
            language=lang_raw,  # type: ignore[arg-type]
            asks_for_compare=bool(payload.get("asks_for_compare")),
            asks_for_dual_evidence=bool(payload.get("asks_for_dual_evidence")),
            asks_for_catalog_resolution=bool(payload.get("asks_for_catalog_resolution")),
            asks_for_workspace_stats=bool(payload.get("asks_for_workspace_stats")),
            asks_for_quotes=bool(payload.get("asks_for_quotes")),
            asks_for_bibliography_gost=bool(payload.get("asks_for_bibliography_gost")),
            asks_for_anchor_free_quote=bool(payload.get("asks_for_anchor_free_quote")),
            asks_for_relations=bool(payload.get("asks_for_relations")),
            asks_for_web_research=bool(payload.get("asks_for_web_research")),
            asks_for_official_product_research=bool(
                payload.get("asks_for_official_product_research")
            ),
            asks_for_arxiv=bool(payload.get("asks_for_arxiv")),
            asks_for_unpaywall=bool(payload.get("asks_for_unpaywall")),
            matched_markers=markers,
        )


def _normalize(text: str) -> str:
    return " ".join(str(text or "").strip().lower().split())


def _detect_language(text: str) -> QuestionLanguage:
    has_ru = bool(_RU_LETTERS.search(text))
    has_en = bool(_EN_LETTERS.search(text))
    if has_ru and has_en:
        # Mixed prompts often contain English paper titles / domain terms inside
        # a Russian instruction. If there are at least a few Cyrillic tokens,
        # keep the answer language Russian instead of drifting to English.
        ru_words = _RU_LETTERS.findall(text)
        if len(ru_words) >= 6:
            return "ru"
        return "mixed"
    if has_ru:
        return "ru"
    if has_en:
        return "en"
    return "unknown"


def _has_any(text: str, markers: tuple[str, ...]) -> tuple[bool, list[str]]:
    hits: list[str] = []
    for needle in markers:
        if needle and needle in text:
            hits.append(needle)
    return (bool(hits), hits)


def _match_external_research_intent(qn: str) -> tuple[bool, bool, bool, list[str]]:
    """Return (asks_web, asks_arxiv, asks_unpaywall, marker_hits)."""
    hits: list[str] = []
    wr_ru, h_ru = _has_any(qn, WEB_RESEARCH_MARKERS_RU)
    hits.extend(h_ru)
    wr_en, h_en = _has_any(qn, WEB_RESEARCH_MARKERS_EN)
    hits.extend(h_en)
    asks_web = bool(wr_ru or wr_en)

    asks_arxiv, h_arx = _has_any(qn, ARXIV_MARKERS)
    hits.extend(h_arx)
    if re.search(r"\d{4}\.\d{4,5}(?:v\d+)?", qn):
        asks_arxiv = True
        hits.append("arxiv_id_shape")

    asks_unpaywall, h_unp = _has_any(qn, UNPAYWALL_LOOKUP_MARKERS)
    hits.extend(h_unp)
    return asks_web, asks_arxiv, asks_unpaywall, hits


def extract_question_features(  # pylint: disable=too-many-locals
    *,
    question: str,
    workspace_id: str | None,
) -> QuestionFeatures:
    """Build :class:`QuestionFeatures` for one user prompt.

    Pure function: no settings, no LLM, no I/O. Safe to call from coordinator,
    planner, supervisor, or tests.
    """
    raw = str(question or "").strip()
    qn = _normalize(raw)
    has_ws = bool(str(workspace_id or "").strip())

    matched: list[str] = []

    asks_compare, hits = _has_any(qn, ("compare", "сравни", "сопоставь"))
    matched.extend(hits)

    asks_dual_ev, hits = _has_any(qn, _DUAL_EVIDENCE_COMPARE_MARKERS)
    matched.extend(hits)

    asks_catalog, hits = _has_any(qn, _CATALOG_RESOLUTION_MARKERS)
    matched.extend(hits)

    asks_ws_stats, hits = _has_any(qn, _WORKSPACE_STATS_MARKERS)
    matched.extend(hits)

    asks_quotes, hits = _has_any(qn, _QUOTE_VERBATIM_MARKERS)
    matched.extend(hits)

    asks_gost, hits = _has_any(qn, _BIBLIOGRAPHY_GOST_MARKERS)
    matched.extend(hits)

    asks_anchor_free, hits = _has_any(qn, _QUOTE_EVIDENCE_MARKERS)
    matched.extend(hits)

    asks_relations = bool(graph_intent_heuristic(raw))
    if asks_relations:
        for needle in _GRAPH_INTENT_HINTS:
            if needle in qn:
                matched.append(needle)
                break

    asks_web, asks_arxiv, asks_unpaywall, ext_hits = _match_external_research_intent(qn)
    matched.extend(ext_hits)

    asks_official_product = bool(asks_web and asks_for_official_product_research(qn))
    if asks_official_product:
        matched.append("official_product_research")

    return QuestionFeatures(
        raw_question=raw,
        normalized_question=qn,
        has_workspace=has_ws,
        language=_detect_language(raw),
        asks_for_compare=asks_compare,
        asks_for_dual_evidence=asks_dual_ev,
        asks_for_catalog_resolution=asks_catalog,
        asks_for_workspace_stats=asks_ws_stats,
        asks_for_quotes=asks_quotes,
        asks_for_bibliography_gost=asks_gost,
        asks_for_anchor_free_quote=asks_anchor_free,
        asks_for_relations=asks_relations,
        asks_for_web_research=asks_web,
        asks_for_official_product_research=asks_official_product,
        asks_for_arxiv=asks_arxiv,
        asks_for_unpaywall=asks_unpaywall,
        matched_markers=tuple(dict.fromkeys(matched)),  # de-dupe, preserve order
    )


__all__ = [
    "QuestionFeatures",
    "QuestionLanguage",
    "extract_question_features",
]
