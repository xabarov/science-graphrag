import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from science_graphrag.settings.service import SettingsService

# Unprefixed keys (MAIN_LLM_*, PHOENIX_*, etc.) must be visible to os.getenv for merge validators.
# override=True: a shell export of MAIN_LLM_API_KEY="" (empty) must not block values from `.env`.
load_dotenv(override=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SCIENCE_GRAPHRAG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Fixed pydantic-settings signature; order dotenv before process env."""

        # Default order is init → env → dotenv: process env overwrites `.env`, so a stale
        # `export SCIENCE_GRAPHRAG_EXTRACTION_LLM_ENABLED=false` defeats local `.env`.
        # Apply dotenv before env so repo `.env` wins over the shell (CI has no secrets `.env`).
        return (
            init_settings,
            dotenv_settings,
            env_settings,
            file_secret_settings,
        )

    blob_root: Path = Field(default=Path("./data/blobs"))
    artifact_root: Path = Field(default=Path("./data/artifacts"))
    database_url: str = Field(
        default="postgresql+psycopg://science:science@localhost:15432/science_graphrag",
    )
    neo4j_uri: str = Field(default="bolt://localhost:17687")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(default="sciencegraphrag")
    qdrant_url: str = Field(default="http://localhost:16333")
    qdrant_collection: str = Field(default="chunks")
    openalex_mailto: str = Field(default="dev@localhost")
    ror_lookup_enabled: bool = Field(
        default=False,
        description="If true, resolve Institution.ror_id via ROR API during ingest (HTTP).",
    )
    use_vl_for_pdf: bool = Field(default=True)
    vl_api_key: str | None = Field(default=None)
    vl_base_url: str = Field(default="https://openrouter.ai/api/v1")
    vl_model: str = Field(default="qwen/qwen3-vl-235b-a22b-instruct")
    vl_max_pages: int = Field(default=16)
    vl_dpi: int = Field(default=144)
    reuse_cached_markdown: bool = Field(
        default=True,
        description="Reuse cached article.md for repeated PDF ingests when available.",
    )
    embedding_model: str | None = Field(
        default=None,
        description="If set, use sentence-transformers; else deterministic hash vectors.",
    )
    chunk_size: int = Field(default=512)
    chunk_overlap: int = Field(default=64)
    front_matter_max_chars: int = Field(
        default=12_000,
        description="Upper bound for metadata/authorships slice (front matter).",
    )
    references_scope_max_chars: int = Field(
        default=90_000,
        description="Upper bound for references/bibliography scope text.",
    )
    chunk_target_tokens: int = Field(
        default=1200,
        description="Target size in approximate tokens for retrieval chunks.",
    )
    chunk_overlap_tokens: int = Field(
        default=140,
        description="Overlap between adjacent chunks within the same section (~tokens).",
    )

    # Stage extraction LLM: markdown -> structured drafts (OpenAI-compatible API).
    extraction_llm_enabled: bool = Field(
        default=True,
        description="LLM-first stage extraction; fallback to heuristics",
    )
    extraction_llm_api_key: str | None = Field(default=None)
    extraction_llm_base_url: str = Field(default="https://openrouter.ai/api/v1")
    extraction_llm_model: str = Field(
        default="mistralai/mistral-small-3.2-24b-instruct",
        description="Text LLM for structured extraction (not necessarily vision)",
    )
    extraction_llm_temperature: float = Field(default=0.0)
    extraction_llm_max_tokens_metadata: int = Field(default=4096)
    extraction_llm_max_tokens_references: int = Field(default=8192)
    extraction_llm_timeout_seconds: float = Field(default=180.0)
    extraction_llm_mode: str = Field(
        default="auto",
        description="Instructor mode override: auto, tools, json, md_json, or openrouter_structured_outputs.",
    )
    extraction_llm_references_batch_size: int = Field(
        default=12,
        ge=1,
        le=100,
        description="Number of reference entries per LLM batch when splitting bibliography extraction.",
    )
    extraction_llm_reference_titles_enabled: bool = Field(
        default=False,
        description="If true, ask LLM to extract reference titles and years in addition to DOI/arXiv ids.",
    )
    extraction_llm_references_merge_policy: str = Field(
        default="conservative",
        description=(
            "How to merge heuristic and LLM references: conservative (no bare LLM-only rows, cap extras) "
            "or union (append unmatched LLM rows like legacy behavior)."
        ),
    )
    extraction_llm_references_merge_max_extra: int = Field(
        default=2,
        ge=0,
        le=50,
        description=(
            "Conservative merge: max rows allowed beyond heuristic count; if exceeded, use enrich-only merge."
        ),
    )
    extraction_llm_references_max_concurrency: int = Field(
        default=1,
        ge=1,
        le=8,
        description="Parallel OpenAI-compatible calls for reference chunks (1 = sequential).",
    )

    # Optional: separate credentials for benchmark teacher gold generation (OpenRouter, etc.).
    benchmark_teacher_llm_api_key: str | None = Field(default=None)
    benchmark_teacher_llm_base_url: str | None = Field(default=None)
    benchmark_teacher_llm_model: str | None = Field(default=None)

    semantic_extraction_enabled: bool = Field(
        default=True,
        description="Run ontology-v1 Method/Dataset stage after layer-1 (ADR 004).",
    )
    semantic_extraction_max_tokens: int = Field(
        default=12_288,
        description="LLM max completion tokens for semantic Method/Dataset (tool JSON must fit).",
    )
    semantic_extraction_temperature: float = Field(default=0.0)
    semantic_graph_confidence_threshold: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="Min confidence to write Method/Dataset nodes and edges to Neo4j.",
    )

    @model_validator(mode="before")
    @classmethod
    def merge_osint_gr_compatible_env(cls, data: Any) -> Any:
        """
        Reuse osint-gr-style env without SCIENCE_GRAPHRAG_ prefix when explicit
        SCIENCE_GRAPHRAG_* keys are absent.
        """
        if not isinstance(data, dict):
            return data

        if not data.get("vl_api_key"):
            key = os.getenv("MAIN_LLM_API_KEY") or os.getenv("API_KEY")
            if key:
                data["vl_api_key"] = key

        if os.getenv("SCIENCE_GRAPHRAG_VL_BASE_URL") is None and os.getenv("MAIN_LLM_BASE_URL"):
            data["vl_base_url"] = os.environ["MAIN_LLM_BASE_URL"].strip().rstrip("/")

        if os.getenv("SCIENCE_GRAPHRAG_VL_MODEL") is None and os.getenv("MAIN_LLM_MODEL"):
            main_model = os.environ["MAIN_LLM_MODEL"].strip()
            if "vl" in main_model.lower() or "vision" in main_model.lower():
                data["vl_model"] = main_model

        if (
            os.getenv("SCIENCE_GRAPHRAG_USE_VL_FOR_PDF") is None
            and os.getenv(
                "USE_VL_FOR_PDF",
            )
            is not None
        ):
            data["use_vl_for_pdf"] = os.getenv("USE_VL_FOR_PDF", "true").lower() in (
                "1",
                "true",
                "yes",
                "on",
            )

        if not data.get("extraction_llm_api_key"):
            ex_key = os.getenv("MAIN_LLM_API_KEY") or os.getenv("API_KEY")
            if ex_key:
                data["extraction_llm_api_key"] = ex_key

        if os.getenv("SCIENCE_GRAPHRAG_EXTRACTION_LLM_BASE_URL") is None and os.getenv(
            "MAIN_LLM_BASE_URL",
        ):
            data["extraction_llm_base_url"] = os.environ["MAIN_LLM_BASE_URL"].strip().rstrip("/")

        if os.getenv("SCIENCE_GRAPHRAG_EXTRACTION_LLM_MODEL") is None and os.getenv(
            "MAIN_LLM_MODEL",
        ):
            data["extraction_llm_model"] = os.environ["MAIN_LLM_MODEL"].strip()

        return data


def get_settings() -> Settings:
    base_settings = Settings()
    service = SettingsService(repo_root=Path(__file__).resolve().parents[1])
    return service.build_runtime_settings(base_settings)
