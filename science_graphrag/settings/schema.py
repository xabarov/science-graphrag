"""Settings UI schema assembly helpers."""

from __future__ import annotations

from typing import Any

from science_graphrag.settings.llm_advanced_fields import advanced_schema_fields


def build_settings_schema() -> dict[str, Any]:
    """Return a UI-friendly schema for runtime settings sections."""
    llm_fields: list[dict[str, Any]] = [
        {"id": "base_url", "type": "url", "required": True, "group": "llm_provider"},
        {"id": "model", "type": "string", "required": True, "group": "llm_provider"},
        {
            "id": "chat_model",
            "type": "string",
            "required": False,
            "group": "llm_provider",
            "description": (
                "Research chat model override; empty uses env "
                "SCIENCE_GRAPHRAG_CHAT_LLM_MODEL or extraction model."
            ),
        },
        {
            "id": "temperature",
            "type": "number",
            "required": True,
            "min": 0.0,
            "max": 2.0,
            "group": "llm_provider",
        },
        {
            "id": "timeout_seconds",
            "type": "number",
            "required": True,
            "min": 1.0,
            "max": 900.0,
            "group": "llm_provider",
            "description": (
                "Shared extraction/provider HTTP transport timeout "
                "(extraction_llm_timeout_seconds)."
            ),
        },
        {
            "id": "vl_model",
            "type": "string",
            "required": False,
            "group": "llm_provider",
            "description": "Vision-language model id for PDF→Markdown (SCIENCE_GRAPHRAG_VL_MODEL).",
        },
        {
            "id": "vl_base_url",
            "type": "url",
            "required": False,
            "group": "llm_provider",
            "description": (
                "OpenAI-compatible base URL for VL; " "defaults to extraction base URL when unset."
            ),
        },
        {"id": "api_key", "type": "secret", "required": False, "group": "llm_provider"},
        {
            "id": "runtime_overrides",
            "type": "object",
            "required": False,
            "group": "llm_provider",
            "description": "Nested map of advanced LLM runtime limits (same keys as Settings).",
        },
    ]
    llm_fields.extend(advanced_schema_fields())
    storage_fields: list[dict[str, Any]] = [
        {"id": "neo4j_uri", "type": "url", "required": False, "group": "neo4j"},
        {"id": "neo4j_user", "type": "string", "required": False, "group": "neo4j"},
        {"id": "neo4j_password", "type": "secret", "required": False, "group": "neo4j"},
        {"id": "qdrant_url", "type": "url", "required": False, "group": "qdrant"},
        {"id": "qdrant_collection", "type": "string", "required": False, "group": "qdrant"},
        {
            "id": "qdrant_claims_collection",
            "type": "string",
            "required": False,
            "group": "qdrant",
        },
        {
            "id": "qdrant_work_embeddings_collection",
            "type": "string",
            "required": False,
            "group": "qdrant",
        },
        {
            "id": "qdrant_author_embeddings_collection",
            "type": "string",
            "required": False,
            "group": "qdrant",
        },
        {"id": "database_url", "type": "secret", "required": False, "group": "postgres"},
        {"id": "redis_url", "type": "url", "required": False, "group": "redis"},
        {"id": "blob_root", "type": "string", "required": False, "group": "paths"},
        {"id": "artifact_root", "type": "string", "required": False, "group": "paths"},
        {"id": "s3_endpoint_url", "type": "url", "required": False, "group": "s3"},
        {"id": "s3_bucket", "type": "string", "required": False, "group": "s3"},
        {"id": "s3_use_ssl", "type": "boolean", "required": False, "group": "s3"},
        {
            "id": "s3_addressing_style",
            "type": "string",
            "required": False,
            "group": "s3",
        },
        {"id": "s3_artifact_key_prefix", "type": "string", "required": False, "group": "s3"},
        {"id": "s3_access_key_id", "type": "string", "required": False, "group": "s3"},
        {"id": "s3_secret_access_key", "type": "secret", "required": False, "group": "s3"},
        {
            "id": "s3_benchmark_runs_key_prefix",
            "type": "string",
            "required": False,
            "group": "s3",
        },
        {
            "id": "s3_diagnostics_key_prefix",
            "type": "string",
            "required": False,
            "group": "s3",
        },
    ]
    benchmark_fields: list[dict[str, Any]] = [
        {
            "id": "by_family",
            "type": "object",
            "required": False,
            "group": "benchmark_defaults",
            "description": (
                "Per-family defaults for benchmark launcher "
                "(model profile, gold, thresholds, API hints)."
            ),
        },
    ]
    agent_tools_fields: list[dict[str, Any]] = [
        {
            "id": "agent_supervisor_max_rounds",
            "type": "integer",
            "required": False,
            "min": 2,
            "max": 32,
            "group": "supervisor",
            "description": (
                "Cap on supervisor routing decisions per turn before writer handoff "
                "(Settings.agent_supervisor_max_rounds)."
            ),
        },
    ]
    return {
        "version": 11,
        "sections": [
            {
                "id": "general",
                "fields": [
                    {
                        "id": "openalex_mailto",
                        "type": "string",
                        "required": True,
                        "group": "openalex",
                        "description": (
                            "Polite-pool contact for OpenAlex HTTP API "
                            "(SCIENCE_GRAPHRAG_OPENALEX_MAILTO when not overridden here)."
                        ),
                    },
                ],
            },
            {
                "id": "llm",
                "fields": llm_fields,
            },
            {
                "id": "ingestion",
                "fields": [
                    {
                        "id": "max_file_size_mb",
                        "type": "integer",
                        "required": True,
                        "min": 1,
                        "max": 2048,
                    },
                    {
                        "id": "claims_extraction_enabled",
                        "type": "boolean",
                        "required": True,
                    },
                ],
            },
            {"id": "storage", "fields": storage_fields},
            {"id": "benchmark", "fields": benchmark_fields},
            {"id": "agent_tools", "fields": agent_tools_fields},
        ],
    }


__all__ = ["build_settings_schema"]
