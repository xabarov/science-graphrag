import os
from pathlib import Path
from typing import Any, Literal

from dotenv import dotenv_values, load_dotenv
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from science_graphrag.settings.service import SettingsService

# Unprefixed keys used by third-party tooling (e.g. PHOENIX_*) may still be read via os.getenv
# outside Settings. For SCIENCE_GRAPHRAG_* fields, pydantic-settings loads `.env` before process env.
# override=True: a shell export of SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY="" (empty) must not
# block values from `.env`.
# Inside Docker, Compose already injects SCIENCE_GRAPHRAG_* (Neo4j/Qdrant hosts); do not let
# load_dotenv clobber them with host-oriented localhost values from a mounted `.env`.
# blob_root / artifact_root are runtime-overridable: an operator or agent may set them
# via shell export for a single ingest run (e.g. SCIENCE_GRAPHRAG_BLOB_ROOT=./blobs_merged).
# load_dotenv(override=True) below would clobber those shell exports; save them first.
_RUNTIME_PATH_VARS = ("SCIENCE_GRAPHRAG_BLOB_ROOT", "SCIENCE_GRAPHRAG_ARTIFACT_ROOT")
_saved_runtime_paths = {k: os.environ[k] for k in _RUNTIME_PATH_VARS if k in os.environ}

_skip_host_dotenv = (
    Path("/.dockerenv").is_file() or os.getenv("SCIENCE_GRAPHRAG_SKIP_HOST_DOTENV") == "1"
)
if _skip_host_dotenv:
    # Load `.env` without clobbering Compose-injected service URLs.
    load_dotenv(override=False)
    # Separately ensure canonical LLM/VL credential vars from `.env` are visible when the shell
    # exported them empty (override=False would otherwise leave os.environ blocking dotenv).
    _api_key_vars = (
        "SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY",
        "SCIENCE_GRAPHRAG_EXTRACTION_LLM_BASE_URL",
        "SCIENCE_GRAPHRAG_EXTRACTION_LLM_MODEL",
        "SCIENCE_GRAPHRAG_VL_API_KEY",
        "SCIENCE_GRAPHRAG_VL_BASE_URL",
        "SCIENCE_GRAPHRAG_VL_MODEL",
        "SCIENCE_GRAPHRAG_USE_VL_FOR_PDF",
        "SCIENCE_GRAPHRAG_OPENROUTER_EMBEDDING_MODEL",
        "SCIENCE_GRAPHRAG_BENCHMARK_TEACHER_LLM_API_KEY",
        "SCIENCE_GRAPHRAG_BENCHMARK_TEACHER_LLM_BASE_URL",
        "SCIENCE_GRAPHRAG_BENCHMARK_TEACHER_LLM_MODEL",
    )
    _env_file_vals = dotenv_values()
    for _k in _api_key_vars:
        if _k in _env_file_vals and not os.environ.get(_k):
            os.environ[_k] = _env_file_vals[_k]
    del _api_key_vars, _env_file_vals, _k
else:
    load_dotenv(override=True)
    # Restore runtime-overridable paths that load_dotenv(override=True) may have clobbered.
    for _k, _v in _saved_runtime_paths.items():
        os.environ[_k] = _v

del _saved_runtime_paths


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
    redis_url: str = Field(default="redis://localhost:6379/0")
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
        description="LX1: default async cap for generic LLM bursts (see utils/llm_semaphore.py).",
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
        default=4096,
        ge=256,
        le=16384,
        description="Max completion tokens for claims extraction LLM call (BT6 benchmarks may need 8k–16k).",
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
    agent_runtime: str = Field(default="langgraph_supervisor_v1")
    agent_max_tool_calls: int = Field(default=8, ge=1, le=30)
    agent_semantic_query_fast_route: bool = Field(
        default=False,
        description=(
            "When true, the LangGraph supervisor may route the first turn to retrieval_agent "
            "without an extra LLM routing call when the user message matches a semantic-only "
            "heuristic (no graph-intent keywords). Reduces latency; enable explicitly for prod "
            "after validating your scenario mix."
        ),
    )
    agent_step_timeout_seconds: float = Field(
        default=120.0,
        ge=1.0,
        le=900.0,
        description=(
            "Wall-clock seconds for one full LangGraph agent turn (sync invoke or SSE stream "
            "collection). Not per-node; see runbook. Default 120s allows multi-tool research turns."
        ),
    )
    agent_supervisor_recursion_limit: int = Field(default=32, ge=4, le=128)
    agent_supervisor_max_rounds: int = Field(
        default=10,
        ge=2,
        le=32,
        description=(
            "Hard cap on supervisor routing decisions (entries in routing_log with from=supervisor) "
            "before forcing writer_agent to avoid endless specialist ping-pong."
        ),
    )
    agent_chat_temperature: float = Field(default=0.0, ge=0.0, le=1.0)
    agent_chat_max_tokens: int = Field(default=1024, ge=64, le=8192)
    agent_rule_tool_search_enabled: bool = Field(
        default=True,
        description="Wave A CH3: rule-based shortlist before bind_tools for specialist subgraphs.",
    )
    agent_turn_policy_classifier: str = Field(
        default="rules_v0",
        description=(
            "Coordinator TurnPolicy source: `rules_v0` (regex/heuristic only), `hybrid_v1` "
            "(narrow deterministic + LLM for fuzzy turns when LLM enabled), `llm_v1` "
            "(LLM for all non-trivial turns except explicit research fast-path)."
        ),
    )
    agent_turn_policy_llm_enabled: bool = Field(
        default=False,
        description="When true with hybrid_v1/llm_v1, run structured LLM turn classifier (requires API key).",
    )
    agent_turn_policy_confidence_threshold: float = Field(
        default=0.65,
        ge=0.0,
        le=1.0,
        description="Minimum classifier confidence to accept LLM turn policy over rules_v0 fuzzy branch.",
    )
    agent_turn_policy_classifier_timeout_seconds: float = Field(
        default=12.0,
        ge=1.0,
        le=120.0,
        description="HTTP timeout for coordinator LLM classifier calls.",
    )
    agent_session_memory_backend: str = Field(
        default="memory",
        description=(
            "CH4 persistence: `memory` (process-local dict) or `redis` (shared store via redis_url). "
            "Falls back to memory if Redis is unreachable at startup."
        ),
    )
    agent_session_redis_key_prefix: str = Field(
        default="science_graphrag:agent_session:v1",
        description="Redis key prefix for thread session JSON (one key per thread_id).",
    )
    agent_session_redis_ttl_seconds: int = Field(
        default=604_800,
        ge=300,
        le=2_592_000,
        description="TTL (seconds) for each agent session Redis key; refreshed on every turn.",
    )
    agent_compaction_rolling_memory_min_digests: int = Field(
        default=3,
        ge=1,
        le=10,
        description="CH5: include rolling_memory in context_compacted.kinds after this many digests.",
    )
    agent_compaction_digest_cap: int = Field(
        default=10,
        ge=3,
        le=50,
        description="CH5: digest window size (matches store cap); boundary_candidate when full.",
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


def get_settings() -> Settings:
    base_settings = Settings()
    service = SettingsService(repo_root=Path(__file__).resolve().parents[1])
    return service.build_runtime_settings(base_settings)
