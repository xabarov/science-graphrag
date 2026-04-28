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


class SettingsSchemaResponse(BaseModel):
    version: int
    sections: list[dict[str, Any]]


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
