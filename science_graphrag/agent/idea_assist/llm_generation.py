from __future__ import annotations

import json
from typing import Any

from science_graphrag.agent.idea_assist.contracts import IDEA_ASSIST_SYSTEM, IdeaAssistLLMResponse
from science_graphrag.config import Settings
from science_graphrag.ingestion.llm.extractor import (
    EXTRACT_MAYBE_MAX_INNER_ATTEMPTS,
    SyncInstructorExtractor,
)
from science_graphrag.llm.concurrency import llm_pool_slot
from science_graphrag.observability.phoenix_tracer import SpanAttributes, llm_span
from science_graphrag.utils.llm_deadline import MonotonicDeadline


def run_idea_assist_llm(
    *,
    settings: Settings,
    workspace_id: str,
    seed_topic: str,
    mode: str,
    max_candidates: int,
    claims: list[dict[str, Any]],
    contradictions: list[dict[str, Any]],
) -> IdeaAssistLLMResponse:
    """Run idea-assist synthesis LLM call and return parsed response."""
    if not settings.extraction_llm_api_key:
        return IdeaAssistLLMResponse()
    extractor = SyncInstructorExtractor(
        api_key=settings.extraction_llm_api_key,
        base_url=settings.extraction_llm_base_url,
        model=settings.extraction_llm_model,
        temperature=0.0,
        max_tokens=min(4096, settings.extraction_llm_max_tokens_references),
        timeout_seconds=settings.extraction_llm_timeout_seconds,
        mode=settings.extraction_llm_mode,
    )
    transport_s = float(settings.extraction_llm_timeout_seconds)
    op_budget = min(900.0, transport_s * float(EXTRACT_MAYBE_MAX_INNER_ATTEMPTS))
    op_deadline = MonotonicDeadline.from_budget_seconds(op_budget)
    claims_preview = claims[:80]
    user = json.dumps(
        {
            "workspace_id": workspace_id,
            "seed_topic": seed_topic,
            "mode": mode,
            "max_candidates": max_candidates,
            "claims": claims_preview,
            "existing_contradictions": contradictions[:40],
        },
        ensure_ascii=False,
    )
    with llm_span(
        "llm.idea_assist",
        {
            **SpanAttributes.llm_runtime_policy_attributes(
                pool_name="idea_assist",
                transport_timeout_seconds=transport_s,
                timeout_contract="transport_with_operation_deadline",
                retry_extra_budget=0,
                operation_deadline_seconds=op_budget,
                transport_max_attempts=EXTRACT_MAYBE_MAX_INNER_ATTEMPTS,
            ),
        },
    ):
        with llm_pool_slot("idea_assist", settings):
            parsed, err = extractor.extract_maybe(
                IdeaAssistLLMResponse,
                system=IDEA_ASSIST_SYSTEM,
                user=user,
                per_attempt_timeout_seconds=transport_s,
                operation_deadline=op_deadline,
            )
    if err or parsed is None:
        return IdeaAssistLLMResponse()
    return parsed
