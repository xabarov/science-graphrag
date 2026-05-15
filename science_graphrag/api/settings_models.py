"""Pydantic models for settings endpoints."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from science_graphrag.api.settings_llm_runtime_patch import LlmRuntimeOverridesPatch


class SettingsSnapshotResponse(BaseModel):
    sections: list[dict[str, Any]]
    llm: dict[str, Any]
    ingestion: dict[str, Any] = Field(default_factory=dict)
    general: dict[str, Any] = Field(
        default_factory=dict,
        description="Non-secret general runtime overrides (e.g. OpenAlex mailto).",
    )
    storage: dict[str, Any] = Field(
        default_factory=dict,
        description="Neo4j, Qdrant, Postgres, Redis, paths, and S3 integration (masked secrets).",
    )
    benchmark: dict[str, Any] = Field(
        default_factory=dict,
        description="Per-family benchmark launcher defaults (model profile, gold, thresholds, API hints).",
    )
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    security: dict[str, Any] = Field(default_factory=dict)
    work_dedup: dict[str, Any] = Field(
        default_factory=dict,
        description="Wave L dedup thresholds and Qdrant collection names (read-only from env).",
    )
    agent_tools: dict[str, Any] = Field(
        default_factory=dict,
        description="Persisted operator knobs for agent runtime (separate from llm.runtime_overrides).",
    )


class SettingsSchemaResponse(BaseModel):
    version: int
    sections: list[dict[str, Any]]


class ExternalResearchSourcesPatch(BaseModel):
    """Partial per-source toggles for native external scholarly HTTP tools."""

    model_config = ConfigDict(extra="forbid")

    crossref: bool | None = None
    arxiv: bool | None = None
    unpaywall: bool | None = None
    openalex: bool | None = None


class UpdateAgentToolsSettingsRequest(BaseModel):
    """Persisted agent_tools allowlist (partial PATCH supported)."""

    model_config = ConfigDict(extra="forbid")

    agent_supervisor_max_rounds: int | None = Field(
        default=None,
        ge=2,
        le=32,
        description=(
            "Max supervisor routing legs per turn before writer handoff "
            "(Settings.agent_supervisor_max_rounds)."
        ),
    )
    external_research_default_enabled: bool | None = Field(
        default=None,
        description=(
            "Default external scholarly tools when the client omits per-request "
            "``web_research_enabled`` (null)."
        ),
    )
    external_research_sources: ExternalResearchSourcesPatch | None = Field(
        default=None,
        description="Partial map for Crossref/arXiv/Unpaywall/OpenAlex tool availability.",
    )
    pdf_reading_mode: Literal["off", "ask", "auto_safe_oa"] | None = Field(
        default=None,
        description="PDF reading in chat (product default; pipeline phases follow).",
    )
    agent_unpaywall_oa_tool_enabled: bool | None = Field(
        default=None,
        description="Register ``unpaywall_lookup`` when true (operator gate).",
    )
    agent_external_http_timeout_seconds: float | None = Field(
        default=None,
        ge=5.0,
        le=120.0,
        description="Shared HTTP timeout for native external scholarly tools.",
    )
    agent_external_max_calls_per_turn: int | None = Field(
        default=None,
        ge=1,
        le=32,
        description="Reserved cap on external tool calls per turn (surfaced in UI).",
    )
    agent_external_max_source_cards: int | None = Field(
        default=None,
        ge=4,
        le=128,
        description="Reserved cap on source cards per answer (surfaced in UI).",
    )
    agent_pdf_read_tool_enabled: bool | None = Field(
        default=None,
        description="Register ``read_external_pdf`` tool when true (operator gate).",
    )
    agent_pdf_read_max_bytes: int | None = Field(
        default=None,
        ge=100_000,
        le=100_000_000,
        description="Max external PDF download size for ``read_external_pdf``.",
    )
    agent_pdf_read_max_pages: int | None = Field(
        default=None,
        ge=1,
        le=500,
        description="Max pages extracted by ``read_external_pdf``.",
    )
    agent_pdf_read_cache_ttl_seconds: int | None = Field(
        default=None,
        ge=0,
        le=86_400,
        description="In-process cache TTL for ``read_external_pdf`` results.",
    )


class UpdateGeneralSettingsRequest(BaseModel):
    openalex_mailto: str = Field(
        ...,
        min_length=3,
        max_length=320,
        description="Contact email for OpenAlex polite-pool (stored in runtime_settings.json).",
    )

    @field_validator("openalex_mailto")
    @classmethod
    def _mailto_shape(cls, value: str) -> str:
        stripped = value.strip()
        if "@" not in stripped or " " in stripped:
            raise ValueError("openalex_mailto must look like a single email address")
        return stripped


class UpdateIngestionSettingsRequest(BaseModel):
    max_file_size_mb: int = Field(
        ...,
        ge=1,
        le=2048,
        description="Per-file limit for POST .../ingest/document (PDF, Markdown, or plain text).",
    )
    claims_extraction_enabled: bool = Field(
        ...,
        description="If true, ingest writes Claim/Evidence rows during the claims stage.",
    )


class UpdateLlmSettingsRequest(BaseModel):
    base_url: HttpUrl
    model: str = Field(..., min_length=1, max_length=256)
    vl_model: str | None = Field(
        default=None,
        max_length=256,
        description="Optional VL model override for PDF→Markdown; empty clears persisted override.",
    )
    vl_base_url: str | None = Field(
        default=None,
        max_length=512,
        description="Optional VL base URL; empty string clears persisted override.",
    )
    chat_model: str | None = Field(
        default=None,
        max_length=256,
        description="Optional research chat model; empty string clears persisted override.",
    )
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    timeout_seconds: float = Field(default=180.0, ge=1.0, le=900.0)
    api_key: str | None = Field(default=None, min_length=1, max_length=4096)
    runtime_overrides: LlmRuntimeOverridesPatch | None = Field(
        default=None,
        description="Optional LLM concurrency, agent, and dedup timeout overrides (Phase 3).",
    )


class TestLlmConnectionRequest(BaseModel):
    base_url: HttpUrl | None = None
    model: str | None = Field(default=None, min_length=1, max_length=256)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    timeout_seconds: float | None = Field(default=None, ge=1.0, le=900.0)
    api_key: str | None = Field(default=None, min_length=1, max_length=4096)
    use_saved_secret: bool = True


class UpdateStorageSettingsRequest(BaseModel):
    """Partial storage and integration update; unset fields are left unchanged."""

    model_config = ConfigDict(extra="ignore")

    neo4j_uri: str | None = Field(default=None, max_length=512)
    neo4j_user: str | None = Field(default=None, max_length=256)
    neo4j_password: str | None = Field(default=None, max_length=2048)
    qdrant_url: str | None = Field(default=None, max_length=512)
    qdrant_collection: str | None = Field(default=None, max_length=256)
    qdrant_claims_collection: str | None = Field(default=None, max_length=256)
    qdrant_work_embeddings_collection: str | None = Field(default=None, max_length=256)
    qdrant_author_embeddings_collection: str | None = Field(default=None, max_length=256)
    database_url: str | None = Field(default=None, max_length=2048)
    redis_url: str | None = Field(default=None, max_length=512)
    blob_root: str | None = Field(default=None, max_length=1024)
    artifact_root: str | None = Field(default=None, max_length=1024)
    s3_endpoint_url: str | None = Field(default=None, max_length=512)
    s3_bucket: str | None = Field(default=None, max_length=256)
    s3_use_ssl: bool | None = None
    s3_addressing_style: Literal["path", "virtual"] | None = None
    s3_artifact_key_prefix: str | None = Field(default=None, max_length=512)
    s3_access_key_id: str | None = Field(default=None, max_length=256)
    s3_secret_access_key: str | None = Field(default=None, max_length=2048)
    s3_benchmark_runs_key_prefix: str | None = Field(default=None, max_length=512)
    s3_diagnostics_key_prefix: str | None = Field(default=None, max_length=512)


class BenchmarkFamilyPrefsUpdate(BaseModel):
    """Partial benchmark defaults for one family; unset fields keep previous persisted values."""

    model_config = ConfigDict(extra="ignore")

    model_profile: str | None = Field(default=None, max_length=256)
    custom_model_id: str | None = Field(default=None, max_length=256)
    gold_source: str | None = Field(default=None, max_length=64)
    threshold_profile: str | None = Field(default=None, max_length=64)
    base_url_override: str | None = Field(default=None, max_length=512)
    api_key_env_name: str | None = Field(default=None, max_length=256)


class UpdateBenchmarkSettingsRequest(BaseModel):
    """PATCH body: only include families you want to update."""

    by_family: dict[str, BenchmarkFamilyPrefsUpdate] = Field(
        default_factory=dict,
        description="Keys: layer1 | layer2 | graph; values are partial field maps (snake_case).",
    )
