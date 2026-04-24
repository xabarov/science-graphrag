"""Pydantic models for settings endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class SettingsSnapshotResponse(BaseModel):
    sections: list[dict[str, Any]]
    llm: dict[str, Any]
    ingestion: dict[str, Any] = Field(default_factory=dict)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    security: dict[str, Any] = Field(default_factory=dict)
    work_dedup: dict[str, Any] = Field(
        default_factory=dict,
        description="Wave L dedup thresholds and Qdrant collection names (read-only from env).",
    )


class SettingsSchemaResponse(BaseModel):
    version: int
    sections: list[dict[str, Any]]


class UpdateIngestionSettingsRequest(BaseModel):
    max_file_size_mb: int = Field(
        ...,
        ge=1,
        le=2048,
        description="Per-file limit for POST .../ingest/document (PDF, Markdown, or plain text).",
    )


class UpdateLlmSettingsRequest(BaseModel):
    base_url: HttpUrl
    model: str = Field(..., min_length=1, max_length=256)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    timeout_seconds: float = Field(default=180.0, ge=1.0, le=900.0)
    api_key: str | None = Field(default=None, min_length=1, max_length=4096)


class TestLlmConnectionRequest(BaseModel):
    base_url: HttpUrl | None = None
    model: str | None = Field(default=None, min_length=1, max_length=256)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    timeout_seconds: float | None = Field(default=None, ge=1.0, le=900.0)
    api_key: str | None = Field(default=None, min_length=1, max_length=4096)
    use_saved_secret: bool = True
