import os
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

import science_graphrag.settings.dotenv_bootstrap  # noqa: F401 — side-effect env bootstrap
from science_graphrag.config_mixins.agent_runtime_fields import AgentRuntimeFields
from science_graphrag.config_mixins.core_storage_fields import CoreStorageFields


class Settings(CoreStorageFields, AgentRuntimeFields, BaseSettings):
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

    openalex_mailto: str = Field(default="dev@localhost")
    ror_lookup_enabled: bool = Field(
        default=False,
        description="If true, resolve Institution.ror_id via ROR API during ingest (HTTP).",
    )
    use_vl_for_pdf: bool = Field(default=True)
    api_key: str | None = Field(
        default=None,
        description=(
            "Canonical unified OpenAI-compatible API key (SCIENCE_GRAPHRAG_API_KEY). "
            "When set, it supplies extraction_llm_api_key unless that field is set separately; "
            "VL calls use vl_api_key when set, otherwise this unified / extraction key."
        ),
    )
    vl_api_key: str | None = Field(default=None)
    vl_base_url: str = Field(default="https://openrouter.ai/api/v1")
    vl_model: str = Field(default="qwen/qwen3-vl-235b-a22b-instruct")
    vl_max_pages: int = Field(default=0, description="0 = no limit; positive = cap at N pages")
    vl_max_tokens: int = Field(default=32768, description="max_tokens for VL API response")
    vl_batch_size: int = Field(
        default=12, description="Pages per VL API call; 0 = all in one request"
    )
    vl_dpi: int = Field(default=144)
    reuse_cached_markdown: bool = Field(
        default=True,
        description="Reuse cached article.md for repeated PDF ingests when available.",
    )
    workspace_upload_max_file_size_mb: int = Field(
        default=128,
        ge=1,
        le=2048,
        description=(
            "Max size for a single workspace document upload (PDF/MD/TXT). "
            "Enforced in the API; reverse proxies (e.g. nginx client_max_body_size) must be >= this."
        ),
    )
    embedding_model: str | None = Field(
        default=None,
        description="If set, use sentence-transformers; else deterministic hash vectors.",
    )
    openrouter_embedding_model: str | None = Field(
        default=None,
        description=(
            "If set, use OpenAI-compatible POST /v1/embeddings via OpenRouter "
            "(same credentials as extraction / benchmark-teacher LLM settings). "
            "Overrides sentence-transformers when both are set."
        ),
    )
    openrouter_embedding_dim: int = Field(
        default=1024,
        ge=32,
        le=8192,
        description="Declared vector size for Qdrant and stores before first embed() (e.g. 1024 for baai/bge-m3).",
    )
    openrouter_embedding_cache_root: Path = Field(
        default=Path("./data/embeddings_cache"),
        description="On-disk cache root for OpenRouterEmbeddingProvider (ingestion / retrieval).",
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
    chunking_engine: Literal["legacy", "chonkie_recursive"] = Field(
        default="chonkie_recursive",
        description='Chunk boundary engine: "chonkie_recursive" (default) or "legacy".',
    )
    chunking_chonkie_recipe: str = Field(
        default="markdown",
        description="Chonkie RecursiveChunker.from_recipe name (e.g. markdown).",
    )
    chunking_chonkie_lang: str = Field(
        default="en",
        description="Chonkie recipe language code (HF hub recipes).",
    )
    chunking_chonkie_min_characters_per_chunk: int = Field(
        default=24,
        ge=8,
        le=4096,
        description="Chonkie min_characters_per_chunk for RecursiveChunker.",
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
    chat_llm_model: str | None = Field(
        default=None,
        description=(
            "Optional OpenRouter-compatible model id for research agent chat. "
            "When unset, ``extraction_llm_model`` is used."
        ),
    )
    chat_llm_base_url: str | None = Field(
        default=None,
        description=(
            "Optional OpenAI-compatible base URL for research chat. "
            "When unset, ``extraction_llm_base_url`` is used."
        ),
    )
    chat_llm_api_key: str | None = Field(
        default=None,
        description=(
            "Optional dedicated API key for research chat. "
            "When unset, ``extraction_llm_api_key`` is used."
        ),
    )
    embeddings_api_key: str | None = Field(
        default=None,
        description=(
            "Optional dedicated API key for embeddings provider. "
            "When unset, embedding providers reuse extraction/teacher keys."
        ),
    )
    chat_llm_temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="When set from persisted LLM chat task, overrides default agent chat sampling.",
    )
    chat_llm_timeout_seconds: float | None = Field(
        default=None,
        ge=5.0,
        le=3600.0,
        description="HTTP timeout for research chat transport when set from persisted LLM chat task.",
    )
    vl_llm_temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for VL PDF calls when set from persisted vision task.",
    )
    vl_llm_timeout_seconds: float | None = Field(
        default=None,
        ge=30.0,
        le=3600.0,
        description="HTTP timeout for VL chat.completions when set from persisted vision task.",
    )
    embeddings_http_base_url: str | None = Field(
        default=None,
        description=(
            "OpenAI-compatible base URL for remote HTTP embeddings; "
            "when unset, extraction/benchmark teacher bases are used."
        ),
    )
    embeddings_http_timeout_seconds: float | None = Field(
        default=None,
        ge=5.0,
        le=600.0,
        description="HTTP timeout for remote embedding provider when set from persisted embeddings task.",
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
        default=True,
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
    llm_concurrency_default: int = Field(
        default=4,
        ge=1,
        le=32,
        description="LX1/Phase2: cap for metadata/vl_pdf/ingestion pool (see science_graphrag/llm/concurrency.py).",
    )
    llm_concurrency_translation: int = Field(
        default=2,
        ge=1,
        le=16,
        description="LX1/LX2: cap parallel translation SSE workers per API process.",
    )
    llm_concurrency_extraction_references: int = Field(
        default=1,
        ge=1,
        le=12,
        description="LX1: mirrors extraction_llm_references_max_concurrency for unified pools.",
    )
    llm_concurrency_claims: int = Field(
        default=2,
        ge=1,
        le=12,
        description="LX1: cap concurrent claims extraction calls.",
    )
    llm_concurrency_summary: int = Field(
        default=2,
        ge=1,
        le=12,
        description="LX1: cap concurrent workspace summary / hypothesis LLM calls.",
    )
    llm_concurrency_semantic: int = Field(
        default=4,
        ge=1,
        le=12,
        description="Phase 2: cap concurrent semantic (Method/Dataset) extraction LLM calls per process.",
    )
    llm_concurrency_dedup: int = Field(
        default=4,
        ge=1,
        le=12,
        description="Phase 2: cap concurrent dedup / adjudication LLM judgments per process.",
    )
    llm_concurrency_agent_chat: int = Field(
        default=8,
        ge=1,
        le=32,
        description="Phase 2: cap concurrent agent chat / supervisor LangChain invokes per process.",
    )
    llm_concurrency_agent_classifier: int = Field(
        default=8,
        ge=1,
        le=16,
        description="Phase 2: cap concurrent turn-policy classifier LLM calls per process.",
    )
    llm_concurrency_query_answer: int = Field(
        default=6,
        ge=1,
        le=12,
        description="Phase 2: cap concurrent grounded query-answer LLM calls per process.",
    )
    llm_distributed_quota_enabled: bool = Field(
        default=False,
        description=(
            "Phase 5: when true, enforce the same per-pool LLM concurrency cap globally via Redis "
            "(see science_graphrag.llm.redis_quota) in addition to process-local semaphores."
        ),
    )
    llm_distributed_quota_key_prefix: str = Field(
        default="science_graphrag:llm_quota:v1",
        min_length=1,
        max_length=200,
        description="Redis key prefix for distributed LLM quota ZSETs (must be safe for Redis keys).",
    )
    llm_distributed_quota_acquire_timeout_seconds: float = Field(
        default=60.0,
        ge=1.0,
        le=600.0,
        description="Max wall-clock wait for a distributed LLM slot before failing the request.",
    )
    llm_distributed_quota_lease_seconds: int = Field(
        default=420,
        ge=30,
        le=3600,
        description=(
            "TTL for each distributed slot lease in Redis (ms score = now + lease); "
            "covers stalled/killed workers without manual cleanup. "
            "v1 does not refresh leases during a long LLM call—set comfortably above worst-case "
            "call duration or accept rare hidden over-cap when a lease expires before the call ends."
        ),
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
    method_ingest_llm_adjudicate: bool = Field(
        default=False,
        description=(
            "If true, run LLM adjudication for method pairs with 0.80<=sim<0.95 during ingest "
            "(ADR 023); otherwise queue for human review only."
        ),
    )

    claims_extraction_enabled: bool = Field(
        default=True,
        description=(
            "If true, run LLM claims extraction after semantic layer and persist Claim/Evidence "
            "to Neo4j + Qdrant claims collection (Wave O)."
        ),
    )
    claims_extraction_max_tokens: int = Field(
        default=8192,
        ge=256,
        le=16384,
        description=(
            "Max completion tokens for claims extraction LLM call. "
            "Truncated JSON / EOF in Phoenix usually means raise this (or cap in extractor_factory); "
            "dense PDF batches may need 8k–16k."
        ),
    )
    qdrant_claims_collection: str = Field(
        default="claims",
        description="Qdrant collection name for claim text embeddings (Wave O).",
    )

    # Wave L — smart dedup (work / author embeddings + LLM judge)
    qdrant_work_embeddings_collection: str = Field(
        default="work_embeddings",
        description="Qdrant collection for one vector per Work (title+abstract+first author summary).",
    )
    qdrant_author_embeddings_collection: str = Field(
        default="author_embeddings",
        description="Qdrant collection for author dedup (L2).",
    )
    work_dedup_sim_low: float = Field(
        default=0.78,
        ge=0.0,
        le=1.0,
        description="Below this cosine similarity, skip pair (no conflict row).",
    )
    work_dedup_sim_high: float = Field(
        default=0.93,
        ge=0.0,
        le=1.0,
        description="At or above: queue as embedding-only high confidence (check_mode=auto_high).",
    )
    work_dedup_max_candidates: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Top-k similar works considered per center work during scan.",
    )
    work_dedup_llm_mode: str = Field(
        default="embedding_with_llm",
        description="One of: embedding_only, embedding_with_llm, llm (middle band uses LLM when embedding_with_llm).",
    )
    work_dedup_llm_timeout_s: float = Field(
        default=30.0,
        ge=1.0,
        le=120.0,
        description="Timeout for LLM same-work judge call.",
    )
    author_dedup_sim_low: float = Field(default=0.75, ge=0.0, le=1.0)
    author_dedup_sim_high: float = Field(default=0.92, ge=0.0, le=1.0)
    author_dedup_max_candidates: int = Field(default=15, ge=1, le=80)
    author_dedup_llm_timeout_s: float = Field(default=30.0, ge=1.0, le=120.0)

    query_answer_llm_enabled: bool = Field(
        default=False,
        description=(
            "If true and extraction LLM credentials are configured, POST /v1/query may run a "
            "second-stage LLM over retrieved citation excerpts (grounded paraphrase)."
        ),
    )
    query_answer_llm_max_tokens: int = Field(default=900, ge=64, le=4096)
    query_answer_llm_temperature: float = Field(default=0.0, ge=0.0, le=1.0)
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1")
    hypothesis_enabled: bool = Field(
        default=False,
        description="Enable Wave S idea-assist endpoint (/v1/agent/idea-assist).",
    )
    idea_assist_live_runtime: bool = Field(
        default=True,
        description="BT10: when false, responses still succeed but run_metadata marks harness/offline.",
    )
    metrics_enabled: bool = Field(
        default=False,
        description="When true, expose GET /metrics (Prometheus text) on the API.",
    )
    gds_enabled: bool = Field(
        default=False,
        description=(
            "If true, allow Neo4j Graph Data Science procedures for large workspace graph "
            "projections when the plugin is installed (otherwise Cypher-only fallback)."
        ),
    )

    admin_api_key: str | None = Field(
        default=None,
        description=(
            "If set, benchmark and settings HTTP routers require matching X-Admin-Key header."
        ),
    )

    @model_validator(mode="before")
    @classmethod
    def merge_runtime_env_overrides(cls, data: Any) -> Any:
        """Apply Docker / operator overrides that must win over mounted `.env` files."""
        if not isinstance(data, dict):
            return data

        # Docker Compose injects service hostnames into the process environment, but
        # pydantic-settings can still end up preferring host-oriented URLs from a mounted
        # `.env`. Force storage URLs from os.environ when running in a container / explicit
        # skip flag (see docker-compose.dev.yml).
        _in_container = Path("/.dockerenv").is_file()
        _skip_dotenv = os.getenv("SCIENCE_GRAPHRAG_SKIP_HOST_DOTENV") == "1"
        if _in_container or _skip_dotenv:
            for field, envar in (
                ("neo4j_uri", "SCIENCE_GRAPHRAG_NEO4J_URI"),
                ("qdrant_url", "SCIENCE_GRAPHRAG_QDRANT_URL"),
                ("database_url", "SCIENCE_GRAPHRAG_DATABASE_URL"),
                ("redis_url", "SCIENCE_GRAPHRAG_REDIS_URL"),
                ("s3_endpoint_url", "SCIENCE_GRAPHRAG_S3_ENDPOINT_URL"),
            ):
                val = os.getenv(envar)
                if val:
                    data[field] = val

        # blob_root / artifact_root are runtime-overridable paths: an operator may point them
        # to a different tree for a single ingest run without editing `.env`.  Pydantic's source
        # order (dotenv > env) would otherwise ignore a shell export.  The module-level code
        # already restores shell-exported values clobbered by load_dotenv(override=True), so
        # os.getenv here reliably reflects the operator's intent in all modes (local / Docker).
        for field, envar in (
            ("blob_root", "SCIENCE_GRAPHRAG_BLOB_ROOT"),
            ("artifact_root", "SCIENCE_GRAPHRAG_ARTIFACT_ROOT"),
        ):
            val = os.getenv(envar)
            if val:
                data[field] = val

        lx_refs = data.get("llm_concurrency_extraction_references")
        leg_refs = data.get("extraction_llm_references_max_concurrency")
        if lx_refs is None and leg_refs is not None:
            data["llm_concurrency_extraction_references"] = leg_refs
        if leg_refs is None and lx_refs is not None:
            data["extraction_llm_references_max_concurrency"] = lx_refs

        # ADR-021: ``SCIENCE_GRAPHRAG_EMBEDDING_MODEL=baai/bge-m3`` maps to ``embedding_model`` but
        # hub-style ids must use the OpenRouter slot so ``resolve_embedder`` picks the API path.
        emb_model = data.get("embedding_model")
        oor = data.get("openrouter_embedding_model")
        if isinstance(emb_model, str) and "/" in emb_model.strip():
            hub = emb_model.strip()
            if oor is None or str(oor).strip() == hub:
                data["openrouter_embedding_model"] = hub
                data.pop("embedding_model", None)

        return data

    @model_validator(mode="after")
    def merge_unified_llm_api_credentials(self) -> "Settings":
        """Apply SCIENCE_GRAPHRAG_API_KEY before legacy extraction_llm_api_key."""

        shared = (self.api_key or "").strip()
        legacy_ex = (self.extraction_llm_api_key or "").strip()
        merged_ex = shared or legacy_ex or None
        object.__setattr__(self, "extraction_llm_api_key", merged_ex)
        return self

    @property
    def resolved_vl_api_key(self) -> str | None:
        """VL-specific key when set; otherwise reuse unified / extraction key."""

        raw_vl = (self.vl_api_key or "").strip()
        if raw_vl:
            return raw_vl
        ex = (self.extraction_llm_api_key or "").strip()
        return ex or None

    @model_validator(mode="after")
    def validate_recursion_limit_against_tool_budget(self) -> "Settings":
        """Catch ``recursion_limit`` set too low for the configured tool budget at startup.

        LangGraph's ``recursion_limit`` counts every node transition (chat, route_*, tools,
        after_tools), not just tool calls. Empirically each ReAct cycle consumes ~4 hops, plus
        a few hops of envelope (entry, final_answer, writer, end). Enforce a conservative
        lower bound ``4 * agent_max_tool_calls + 8`` so misconfigurations fail fast instead of
        producing ``GraphRecursionError`` mid-turn.
        """

        budget = int(self.agent_max_tool_calls)
        recursion_limit = int(self.agent_supervisor_recursion_limit)
        min_required = 4 * budget + 8
        if recursion_limit < min_required:
            raise ValueError(
                "agent_supervisor_recursion_limit too low for agent_max_tool_calls="
                f"{budget}: got {recursion_limit}, need >= {min_required} "
                "(approximation: 4 graph hops per ReAct cycle + 8 hops envelope). "
                "Increase SCIENCE_GRAPHRAG_AGENT_SUPERVISOR_RECURSION_LIMIT or lower "
                "SCIENCE_GRAPHRAG_AGENT_MAX_TOOL_CALLS."
            )
        return self

    @model_validator(mode="after")
    def validate_mandatory_s3_credentials(self) -> "Settings":
        """S3/MinIO credentials and bucket are required for ingest blobs, queue, artifacts, benchmarks."""

        ak = (self.s3_access_key_id or "").strip()
        sk = (self.s3_secret_access_key or "").strip()
        bucket = (self.s3_bucket or "").strip()
        object.__setattr__(self, "s3_access_key_id", ak)
        object.__setattr__(self, "s3_secret_access_key", sk)
        object.__setattr__(self, "s3_bucket", bucket)
        missing: list[str] = []
        if not ak:
            missing.append("s3_access_key_id")
        if not sk:
            missing.append("s3_secret_access_key")
        if not bucket:
            missing.append("s3_bucket")
        if missing:
            raise ValueError(
                "S3/MinIO is mandatory: set non-empty "
                + ", ".join(f"SCIENCE_GRAPHRAG_{m.upper()}" for m in missing)
            )
        return self


def get_settings() -> Settings:
    """Return ``Settings`` with persisted runtime overlays and managed LLM secret applied."""

    from science_graphrag.settings.service import SettingsService

    base_settings = Settings()
    service = SettingsService(repo_root=Path(__file__).resolve().parents[1])
    return service.build_runtime_settings(base_settings)
