"""Deterministic concept/topic harness for benchmark v1 (not production LLM)."""

from __future__ import annotations

from typing import Any


def extract_concepts_topics_anchor_harness(
    article_text: str, gold: dict[str, Any]
) -> dict[str, Any]:
    """Emit predictions for each expected row whose ``anchor_phrase`` appears in ``article_text``.

    Case-insensitive substring match (same pattern as claims harness).
    """

    text_l = (article_text or "").lower()
    concepts: list[dict[str, Any]] = []
    topics: list[dict[str, Any]] = []
    for row in gold.get("expected_concepts") or []:
        if not isinstance(row, dict):
            continue
        cid = row.get("concept_id")
        anchor = str(row.get("anchor_phrase") or "").strip()
        if not cid or not anchor:
            continue
        if anchor.lower() in text_l:
            concepts.append(
                {
                    "concept_id": str(cid),
                    "name": row.get("name"),
                    "normalized_name": row.get("name"),
                },
            )
    for row in gold.get("expected_topics") or []:
        if not isinstance(row, dict):
            continue
        tid = row.get("topic_id")
        anchor = str(row.get("anchor_phrase") or "").strip()
        if not tid or not anchor:
            continue
        if anchor.lower() in text_l:
            topics.append(
                {
                    "topic_id": str(tid),
                    "name": row.get("name"),
                    "normalized_name": row.get("name"),
                },
            )
    return {"concepts": concepts, "topics": topics}
