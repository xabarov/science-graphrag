"""Optional nested PATCH payload for LLM runtime limits (Phase 3)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AgentRuntimeSlug = Literal["langgraph_research_v1", "langgraph_supervisor_v1", "retrieval_v1"]


class LlmRuntimeOverridesPatch(BaseModel):
    """Optional LLM runtime limits nested in ``PATCH /v1/settings/llm`` (Phase 3).

    All fields optional; only set keys are persisted (``exclude_unset`` on dump).
    """

    model_config = ConfigDict(extra="forbid")

    llm_concurrency_default: int | None = Field(default=None, ge=1, le=32)
    llm_concurrency_translation: int | None = Field(default=None, ge=1, le=16)
    llm_concurrency_extraction_references: int | None = Field(default=None, ge=1, le=12)
    llm_concurrency_claims: int | None = Field(default=None, ge=1, le=12)
    llm_concurrency_summary: int | None = Field(default=None, ge=1, le=12)
    llm_concurrency_semantic: int | None = Field(default=None, ge=1, le=12)
    llm_concurrency_dedup: int | None = Field(default=None, ge=1, le=12)
    llm_concurrency_agent_chat: int | None = Field(default=None, ge=1, le=32)
    llm_concurrency_agent_classifier: int | None = Field(default=None, ge=1, le=16)
    llm_concurrency_query_answer: int | None = Field(default=None, ge=1, le=12)
    extraction_llm_references_max_concurrency: int | None = Field(default=None, ge=1, le=8)
    agent_step_timeout_seconds: float | None = Field(default=None, ge=1.0, le=900.0)
    agent_turn_policy_classifier_timeout_seconds: float | None = Field(
        default=None, ge=1.0, le=120.0
    )
    agent_turn_policy_llm_enabled: bool | None = None
    agent_runtime: AgentRuntimeSlug | None = None
    agent_max_tool_calls: int | None = Field(default=None, ge=1, le=30)
    work_dedup_llm_timeout_s: float | None = Field(default=None, ge=1.0, le=120.0)
    author_dedup_llm_timeout_s: float | None = Field(default=None, ge=1.0, le=120.0)
    agent_chat_max_retries: int | None = Field(default=None, ge=0, le=2)
    agent_classifier_max_retries: int | None = Field(default=None, ge=0, le=2)
    agent_graph_invoke_max_workers: int | None = Field(default=None, ge=0, le=32)
    agent_min_llm_hop_reserve_seconds: float | None = Field(default=None, ge=1.0, le=120.0)
    llm_distributed_quota_enabled: bool | None = None
    llm_distributed_quota_key_prefix: str | None = Field(default=None, min_length=1, max_length=200)
    llm_distributed_quota_acquire_timeout_seconds: float | None = Field(
        default=None, ge=1.0, le=600.0
    )
    llm_distributed_quota_lease_seconds: int | None = Field(default=None, ge=30, le=3600)
