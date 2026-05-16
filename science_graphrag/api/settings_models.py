"""Pydantic models for settings endpoints."""

from __future__ import annotations

from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from science_graphrag.api.settings_llm_runtime_patch import LlmRuntimeOverridesPatch
from science_graphrag.settings.agent_tools_mcp import normalize_mcp_server_denylist


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
    semantic_scholar: bool | None = None


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
        description="Partial map for Crossref/arXiv/Unpaywall/OpenAlex/Semantic Scholar tool availability.",
    )
    pdf_reading_mode: Literal["off", "ask", "auto_safe_oa"] | None = Field(
        default=None,
        description="PDF reading in chat (product default; pipeline phases follow).",
    )
    agent_pdf_read_backend_mode: Literal["pypdf", "vl", "hybrid"] | None = Field(
        default=None,
        description="Extraction backend for ``read_external_pdf`` (pypdf / VL / hybrid).",
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
    agent_pdf_read_cache_max_entries: int | None = Field(
        default=None,
        ge=16,
        le=10_000,
        description="Max in-process cached PDF read entries (LRU).",
    )
    agent_pdf_read_durable_cache_enabled: bool | None = Field(
        default=None,
        description=(
            "When true and Redis is configured, persist successful PDF read tool payloads in Redis."
        ),
    )
    agent_mcp_request_timeout_seconds: float | None = Field(
        default=None,
        ge=1.0,
        le=120.0,
        description="HTTP timeout for MCP adapter JSON-RPC calls.",
    )
    agent_mcp_server_denylist: list[str] | None = Field(
        default=None,
        max_length=32,
        description="Substring denylist for MCP server identifiers (operator policy).",
    )

    @field_validator("agent_mcp_server_denylist")
    @classmethod
    def _normalize_mcp_server_denylist(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return normalize_mcp_server_denylist(value)


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


class LlmTaskProviderCard(BaseModel):
    """Partial update for extraction/chat/vision task blocks."""

    model_config = ConfigDict(extra="forbid")

    base_url: str | None = Field(default=None, max_length=512)
    model: str | None = Field(default=None, max_length=256)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    timeout_seconds: float | None = Field(default=None, ge=5.0, le=3600.0)


class LlmEmbeddingsTaskCard(BaseModel):
    """Partial update for embeddings task block (no sampling temperature)."""

    model_config = ConfigDict(extra="forbid")

    mode: Literal["http", "local"] | None = None
    base_url: str | None = Field(default=None, max_length=512)
    model: str | None = Field(default=None, max_length=256)
    timeout_seconds: float | None = Field(default=None, ge=5.0, le=600.0)


class LlmTasksUpdate(BaseModel):
    """Nested task-oriented LLM settings (preferred over legacy flat fields)."""

    model_config = ConfigDict(extra="forbid")

    extraction: LlmTaskProviderCard | None = None
    chat: LlmTaskProviderCard | None = None
    vision: LlmTaskProviderCard | None = None
    embeddings: LlmEmbeddingsTaskCard | None = None


class RevealLlmSecretRequest(BaseModel):
    """Explicit operator action to read a managed vault secret."""

    model_config = ConfigDict(extra="forbid")

    task: Literal["extraction", "chat", "vision", "embeddings"]


class RevealLlmSecretResponse(BaseModel):
    secret: str = Field(default="")


class UpdateLlmSettingsRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    tasks: LlmTasksUpdate | None = None
    base_url: HttpUrl | None = None
    model: str | None = Field(default=None, max_length=256)
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
    chat_base_url: str | None = Field(
        default=None,
        max_length=512,
        description="Optional chat base URL; empty string clears persisted override.",
    )
    embeddings_mode: Literal["openrouter", "local"] | None = Field(
        default=None,
        description="Embeddings mode override; empty clears persisted override.",
    )
    embeddings_model: str | None = Field(
        default=None,
        max_length=256,
        description="Optional embeddings model id; empty string clears persisted override.",
    )
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    timeout_seconds: float | None = Field(default=None, ge=1.0, le=900.0)
    api_key: str | None = Field(default=None, max_length=4096)
    vision_api_key: str | None = Field(
        default=None,
        max_length=4096,
        description=(
            "Managed vision-only API key (omit field to leave unchanged; null or empty clears)."
        ),
    )
    chat_api_key: str | None = Field(
        default=None,
        max_length=4096,
        description=(
            "Managed chat-task API key (omit field to leave unchanged; null or empty clears)."
        ),
    )
    embeddings_api_key: str | None = Field(
        default=None,
        max_length=4096,
        description=(
            "Managed embeddings-task API key (omit field to leave unchanged; null or empty clears)."
        ),
    )
    runtime_overrides: LlmRuntimeOverridesPatch | None = Field(
        default=None,
        description="Optional LLM concurrency, agent, and dedup timeout overrides (Phase 3).",
    )

    @model_validator(mode="after")
    def _tasks_or_legacy(self) -> Self:
        if self.tasks is not None:
            return self
        if self.runtime_overrides is not None:
            return self
        if any(
            x is not None
            for x in (
                self.api_key,
                self.chat_api_key,
                self.vision_api_key,
                self.embeddings_api_key,
            )
        ):
            return self
        if self.base_url is None or not (self.model or "").strip():
            raise ValueError("Provide llm.tasks or legacy base_url and model fields")
        return self


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
