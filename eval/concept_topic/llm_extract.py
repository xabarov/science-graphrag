"""Production concept/topic extraction for benchmarks (LLM, constrained to gold ids)."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from science_graphrag.config import Settings, get_settings
from science_graphrag.ingestion.llm.extractor import SyncInstructorExtractor


class _ConceptRow(BaseModel):
    concept_id: str = Field(..., description="Id from the allowed list in the user prompt")
    name: str = Field(default="", max_length=400)


class _TopicRow(BaseModel):
    topic_id: str = Field(..., description="Id from the allowed list in the user prompt")
    name: str = Field(default="", max_length=400)


class _ConceptTopicLLMResponse(BaseModel):
    concepts: list[_ConceptRow] = Field(default_factory=list)
    topics: list[_TopicRow] = Field(default_factory=list)


def extract_concepts_topics_llm(article_text: str, gold: dict[str, Any], *, settings: Settings | None = None) -> dict[str, Any]:
    """Return ``{concepts:[], topics:[]}`` using extraction LLM; ids must match gold expected rows."""

    s = settings or get_settings()
    if not s.extraction_llm_api_key or not s.extraction_llm_enabled:
        return {"concepts": [], "topics": []}

    allowed_concepts: list[dict[str, str]] = []
    for row in gold.get("expected_concepts") or []:
        if not isinstance(row, dict):
            continue
        cid = str(row.get("concept_id") or "").strip()
        if cid:
            allowed_concepts.append({"concept_id": cid, "name": str(row.get("name") or "")})

    allowed_topics: list[dict[str, str]] = []
    for row in gold.get("expected_topics") or []:
        if not isinstance(row, dict):
            continue
        tid = str(row.get("topic_id") or "").strip()
        if tid:
            allowed_topics.append({"topic_id": tid, "name": str(row.get("name") or "")})

    concept_ids = {x["concept_id"] for x in allowed_concepts}
    topic_ids = {x["topic_id"] for x in allowed_topics}

    system = (
        "You extract research concepts and research topics from a scientific paper excerpt. "
        "Return ONLY entries whose id appears in the allowed lists and that the excerpt clearly supports. "
        "If the excerpt does not support an id, omit it. If nothing matches, return empty arrays."
    )
    user = (
        "Allowed concept ids (use only these concept_id values):\n"
        + json.dumps(allowed_concepts, ensure_ascii=False, indent=2)
        + "\n\nAllowed topic ids (use only these topic_id values):\n"
        + json.dumps(allowed_topics, ensure_ascii=False, indent=2)
        + "\n\nArticle excerpt:\n\n"
        + (article_text or "")[:24000]
    )
    ext = SyncInstructorExtractor(
        api_key=s.extraction_llm_api_key,
        base_url=s.extraction_llm_base_url,
        model=s.extraction_llm_model,
        temperature=0.0,
        max_tokens=4096,
        timeout_seconds=min(float(s.extraction_llm_timeout_seconds), 120.0),
        mode=s.extraction_llm_mode,
    )
    parsed, err = ext.extract_maybe(_ConceptTopicLLMResponse, system=system, user=user)
    if err or parsed is None:
        return {"concepts": [], "topics": []}

    concepts_out = [
        {
            "concept_id": c.concept_id.strip(),
            "name": (c.name.strip() or c.concept_id.strip()),
            "normalized_name": (c.name.strip() or c.concept_id.strip()),
        }
        for c in parsed.concepts
        if c.concept_id.strip() in concept_ids
    ]
    topics_out = [
        {
            "topic_id": t.topic_id.strip(),
            "name": (t.name.strip() or t.topic_id.strip()),
            "normalized_name": (t.name.strip() or t.topic_id.strip()),
        }
        for t in parsed.topics
        if t.topic_id.strip() in topic_ids
    ]
    return {"concepts": concepts_out, "topics": topics_out}
