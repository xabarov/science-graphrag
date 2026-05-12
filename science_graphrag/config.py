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
        "SCIENCE_GRAPHRAG_API_KEY",
        "SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY",
        "SCIENCE_GRAPHRAG_EXTRACTION_LLM_BASE_URL",
        "SCIENCE_GRAPHRAG_EXTRACTION_LLM_MODEL",
        "SCIENCE_GRAPHRAG_CHAT_LLM_MODEL",
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
    s3_endpoint_url: str | None = Field(
        default=None,
        description="S3 API endpoint (e.g. http://localhost:19000 for MinIO).",
    )
    s3_access_key_id: str = Field(
        description="Required. S3/MinIO access key (SCIENCE_GRAPHRAG_S3_ACCESS_KEY_ID).",
    )
    s3_secret_access_key: str = Field(
        description="Required. S3/MinIO secret key (SCIENCE_GRAPHRAG_S3_SECRET_ACCESS_KEY).",
    )
    s3_bucket: str = Field(
        default="science-raw", description="Bucket for ingest queue + raw sha blobs."
    )
    s3_use_ssl: bool = Field(
        default=True,
        description="Set false for plain-http MinIO in dev.",
    )
    s3_addressing_style: Literal["path", "virtual"] = Field(
        default="path",
        description="MinIO typically needs path-style addressing.",
    )
    s3_artifact_key_prefix: str = Field(
        default="science-artifacts",
        description=(
            "Object key prefix inside s3_bucket for ingest artifacts (article.md, normalized.md, "
            "diagnostics). Same bucket as Phase 1 raw/queue; distinct prefix per roadmap §7.2."
        ),
    )
    s3_benchmark_runs_key_prefix: str = Field(
        default="science-benchmarks",
        description="Object key prefix inside s3_bucket for UI benchmark run full.json payloads.",
    )
    s3_diagnostics_key_prefix: str = Field(
        default="science-diagnostics",
        description="Object key prefix for OD/chat-agent diagnostic dumps (CLI scripts).",
    )
    object_storage_diagnostics_retention_days: int = Field(
        default=30,
        ge=0,
        description=(
            "Phase 4: optional hint (object tag/metadata) for diagnostic S3 objects; "
            "GC scripts may use this with LastModified. 0 = omit hint tag."
        ),
    )
    object_storage_benchmark_full_retention_days: int = Field(
        default=90,
        ge=0,
        description=("Phase 4: optional hint for benchmark full.json in S3; 0 = omit hint tag."),
    )
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
    agent_runtime: str = Field(
        default="langgraph_supervisor_v3",
        description=(
            "LangGraph agent wiring (default ``langgraph_supervisor_v3`` per ADR-029, "
            "2026-05-08 single-supervisor backbone): "
            "``langgraph_supervisor_v3`` (multi-agent supervisor with v3 subagent observability, "
            "default), ``langgraph_supervisor_v1`` (legacy multi-specialist, kept for "
            "regression baselines), ``langgraph_research_v1`` (single-agent ReAct + tools, used "
            "for explicit ReAct comparison runs), or ``retrieval_v1`` (legacy non-graph "
            "harness)."
        ),
    )
    agent_max_parallel_subagents: int = Field(
        default=4,
        ge=1,
        le=16,
        description=(
            "Hard cap on concurrent explicit ``spawn_subagent`` children per parent turn "
            "(Train T3 B1). Routing legs remain sequential; this bounds future parallel fan-out."
        ),
    )
    agent_subagent_lifecycle_enhanced_enabled: bool = Field(
        default=True,
        description=(
            "When ``agent_runtime=langgraph_supervisor_v3``, emit task-notification HumanMessages, "
            "mandatory subagent sidechain lifecycle rows (if sidechain transcripts enabled), "
            "and extended SSE observability (see stream_lifecycle)."
        ),
    )
    agent_subagent_carry_back_max_chars: int = Field(
        default=4000,
        ge=500,
        le=50_000,
        description="Max chars serialized into structured carry-back ``result_excerpt`` for subagent legs.",
    )
    agent_subagent_stream_heartbeat_interval_seconds: float = Field(
        default=15.0,
        ge=0.0,
        le=120.0,
        description=(
            "SSE subagent_heartbeat interval while a routing leg is active (v3 only). "
            "0 disables heartbeats."
        ),
    )
    agent_subagent_progress_label_enabled: bool = Field(
        default=True,
        description="When true (v3), emit throttled deterministic subagent_progress_label events on new tool progress.",
    )
    agent_subagent_progress_label_interval_seconds: float = Field(
        default=30.0,
        ge=30.0,
        le=300.0,
        description="Minimum seconds between subagent_progress_label emissions per leg.",
    )
    agent_subagent_coordinator_lane_stub_enabled: bool = Field(
        default=False,
        description=(
            "Synthetic coordinator-mode observability lane marker for fork-vs-coordinator benchmarks; "
            "does not enable real coordinator runtime."
        ),
    )
    agent_claim_verification_enabled: bool = Field(
        default=False,
        description=(
            "When true (supervisor v3), run read-only claim_verification subagent after retrieval "
            "tool payloads and merge into specialist_results_v3 + run_metadata."
        ),
    )
    agent_claim_verification_max_tool_calls: int = Field(
        default=6,
        ge=1,
        le=16,
        description="Tool budget for each claim_verification child ReAct subgraph.",
    )
    agent_claim_verification_step_timeout_seconds: float = Field(
        default=60.0,
        ge=5.0,
        le=300.0,
        description="Wall-clock invoke deadline per claim_verification child subgraph.",
    )
    agent_claim_verification_recursion_limit: int = Field(
        default=24,
        ge=4,
        le=64,
        description="LangGraph recursion_limit for claim_verification subgraph.",
    )
    agent_claim_verification_fanout_max: int = Field(
        default=1,
        ge=1,
        le=8,
        description="Max parallel claim_verification passes per retrieval hop (fanout research cap).",
    )
    agent_corpus_explore_enabled: bool = Field(
        default=False,
        description=(
            "When true (supervisor v3), run read-only corpus_explore subagent after retrieval "
            "with a cheap model + narrow tools (Train T4 §10.3)."
        ),
    )
    agent_corpus_explore_chat_llm_model: str | None = Field(
        default=None,
        description=(
            "Optional OpenRouter model id for corpus_explore child (defaults to chat model). "
            "Use a small/fast model for cost/latency."
        ),
    )
    agent_corpus_explore_chat_max_tokens: int = Field(
        default=768,
        ge=64,
        le=4096,
        description="Max tokens for corpus_explore assistant completion.",
    )
    agent_corpus_explore_chat_temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Temperature for corpus_explore subagent.",
    )
    agent_corpus_explore_max_tool_calls: int = Field(
        default=10,
        ge=1,
        le=24,
        description="Tool budget per corpus_explore child ReAct subgraph.",
    )
    agent_corpus_explore_step_timeout_seconds: float = Field(
        default=90.0,
        ge=5.0,
        le=300.0,
        description="Wall-clock invoke deadline per corpus_explore subgraph.",
    )
    agent_corpus_explore_recursion_limit: int = Field(
        default=28,
        ge=4,
        le=64,
        description="LangGraph recursion_limit for corpus_explore subgraph.",
    )
    agent_corpus_explore_fanout_max: int = Field(
        default=1,
        ge=1,
        le=8,
        description="Max corpus_explore passes per retrieval hop.",
    )
    agent_research_plan_subagent_enabled: bool = Field(
        default=False,
        description=(
            "When true (supervisor v3), run research-plan decomposition subagent "
            "(corpus/graph/writer sections; optional research_plan_write)."
        ),
    )
    agent_research_plan_subagent_chat_llm_model: str | None = Field(
        default=None,
        description="Optional model override for research-plan subagent (defaults to chat model).",
    )
    agent_research_plan_subagent_chat_max_tokens: int = Field(
        default=1400,
        ge=64,
        le=8192,
        description="Max tokens for research-plan subagent completion.",
    )
    agent_research_plan_subagent_chat_temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )
    agent_research_plan_subagent_max_tool_calls: int = Field(
        default=14,
        ge=1,
        le=32,
        description="Tool budget per research-plan child subgraph.",
    )
    agent_research_plan_subagent_step_timeout_seconds: float = Field(
        default=120.0,
        ge=5.0,
        le=600.0,
        description="Wall-clock invoke deadline per research-plan subgraph.",
    )
    agent_research_plan_subagent_recursion_limit: int = Field(
        default=36,
        ge=4,
        le=96,
        description="LangGraph recursion_limit for research-plan subgraph.",
    )
    agent_research_plan_subagent_fanout_max: int = Field(
        default=1,
        ge=1,
        le=8,
        description="Max research-plan passes per retrieval hop.",
    )
    agent_tool_use_summary_enabled: bool = Field(
        default=False,
        description=(
            "When true, compress oversized JSON tool results via cache-safe side-LLM summary "
            "(§10.9), complementing token-budget compaction."
        ),
    )
    agent_tool_use_summary_min_payload_chars: int = Field(
        default=6000,
        ge=500,
        le=500_000,
        description="Apply tool_use_summary only when ToolMessage JSON serialized length exceeds this.",
    )
    agent_tool_use_summary_max_output_chars: int = Field(
        default=2800,
        ge=200,
        le=50_000,
        description="Cap for summarized JSON embedded back into ToolMessage.",
    )
    agent_tool_use_summary_llm_temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Temperature for tool_use_summary side-LLM.",
    )
    agent_writer_terminal_single_pass_shadow_enabled: bool = Field(
        default=False,
        description=(
            "Wave E / trace-review A/B: writer specialist ends after the first tool execution "
            "batch (no additional chat→tools repair hops). Operator-only; default off."
        ),
    )
    agent_max_tool_calls: int = Field(default=12, ge=1, le=30)
    agent_route_plan_enabled: bool = Field(
        default=True,
        description=(
            "Phase 1 (orchestration stabilization 2026-05-07): when true, "
            "``build_initial_agent_state`` writes a deterministic ``RoutePlan`` "
            "(see ``science_graphrag.agent.coordination.route_planner``) into "
            "``metadata.turn_policy.route_plan`` and the supervisor reads it for "
            "first-hop / writer-handoff decisions. Default-on as of 2026-05-08 "
            "(orchestration tail closure). Setting to false disables the new "
            "planner path and relies entirely on the legacy compatibility shims."
        ),
    )
    agent_route_plan_post_retrieval_handoff_enabled: bool = Field(
        default=True,
        description=(
            "Phase 1.4: when true and a RoutePlan is attached, ``supervisor_node`` "
            "uses the planner's ``planner_post_retrieval_handoff`` (consumer of "
            "QuestionFeatures + tool_counts) instead of the legacy "
            "``_maybe_force_writer_after_retrieval`` heuristic. Default-on as of "
            "2026-05-08 (orchestration tail closure)."
        ),
    )
    agent_supervisor_replan_only_llm_enabled: bool = Field(
        default=True,
        description=(
            "Phase 4: when true and a RoutePlan is attached, the supervisor only "
            "invokes the LLM router when the plan raises ``replan_signal`` (or "
            "terminates without a next step). Otherwise it follows the plan steps "
            "deterministically. Default-on as of 2026-05-08 (orchestration tail "
            "closure); open-ended ``default_supervisor_round_cap`` plans still "
            "defer to the LLM router after step 0."
        ),
    )
    agent_per_tool_call_timeout_seconds: float = Field(
        default=0.0,
        ge=0.0,
        le=600.0,
        description=(
            "Phase 6: optional per-tool-call wall-clock cap inside "
            "``tool_execution_pipeline``. ``0`` disables the cap (the global "
            "``agent_step_timeout_seconds`` still applies). When set, a single "
            "stuck tool no longer eats the whole turn — it raises a typed "
            "``permission_denied``-style ToolMessage with reason "
            "``per_tool_deadline_exceeded`` and the planner can fall back to "
            "salvage."
        ),
    )
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
        default=240.0,
        ge=1.0,
        le=900.0,
        description=(
            "Wall-clock seconds for one full LangGraph agent turn (sync invoke or SSE stream "
            "collection). Not per-node; see runbook. Default 240s allows multi-tool research turns."
        ),
    )
    agent_supervisor_recursion_limit: int = Field(
        default=64,
        ge=4,
        le=128,
        description=(
            "LangGraph ``invoke`` ``recursion_limit`` (counts all graph node transitions, not only "
            "tool calls). Increase via env if runs fail with GRAPH_RECURSION_LIMIT while below "
            "tool budget."
        ),
    )
    agent_supervisor_max_rounds: int = Field(
        default=10,
        ge=2,
        le=32,
        description=(
            "Hard cap on supervisor routing decisions (entries in routing_log with from=supervisor) "
            "before forcing writer_agent to avoid endless specialist ping-pong."
        ),
    )
    agent_react_max_consecutive_same_batch: int = Field(
        default=2,
        ge=1,
        le=8,
        description=(
            "ReAct soft-cap: how many times the same tool+args batch may repeat before the next "
            "route forces ``final_answer_nudge``. Pre-empts ``GraphRecursionError`` on loops."
        ),
    )
    agent_react_max_total_hops: int = Field(
        default=12,
        ge=2,
        le=64,
        description=(
            "ReAct soft-cap: total tool batches per turn after which the next route forces "
            "``final_answer_nudge``. Pre-empts hard ``recursion_limit`` exhaustion."
        ),
    )
    agent_chat_temperature: float = Field(default=0.0, ge=0.0, le=1.0)
    agent_chat_max_tokens: int = Field(default=1024, ge=64, le=8192)
    agent_rule_tool_search_enabled: bool = Field(
        default=True,
        description=(
            "Wave A CH3: rule-based shortlist before bind_tools for specialist subgraphs; "
            "when enabled, single-agent ReAct also binds a per-turn shortlist (see tool_search)."
        ),
    )
    agent_tool_search_score_band: float = Field(
        default=1.35,
        ge=0.25,
        le=5.0,
        description=(
            "Rule-based tool shortlist: keep tools with score >= top_score - band "
            "(see science_graphrag.agent.tool_search). Habr Jun 2026 default 1.35 vs legacy ~1.5."
        ),
    )
    agent_tool_search_deferred_schema_refs_enabled: bool = Field(
        default=False,
        description=(
            "When true, tool_search debug metadata emits deferred schema refs for shortlist-picked "
            "tools (catalog-first prompt contract, full JSON schemas only for selected tools)."
        ),
    )
    agent_tool_search_deferred_schema_full_on_discovery_enabled: bool = Field(
        default=True,
        description=(
            "When true with deferred_schema_refs, attach full JSON Schema in tool_search_result "
            "metadata only for strict-deferred tools merged via message discovery or session "
            "carry-over (compact refs otherwise). See Epic C2 only-on-discovery transport."
        ),
    )
    agent_tool_search_deferred_schema_full_max_bytes_per_tool: int = Field(
        default=24_000,
        ge=512,
        le=200_000,
        description=(
            "Per-tool cap for embedded json_schema bytes in deferred_schema_full_tools "
            "(skipped when larger)."
        ),
    )
    agent_tool_search_llm_rerank_enabled: bool = Field(
        default=False,
        description=(
            "Epic C1: after rule-based shortlist, optionally call a small JSON-only LLM judge to "
            "rerank tools within the candidate pool (see tool_selector_hybrid)."
        ),
    )
    agent_tool_search_llm_rerank_max_candidates: int = Field(
        default=12,
        ge=4,
        le=32,
        description="Max tools passed into the LLM rerank prompt (capped from the rule shortlist).",
    )
    agent_tool_search_llm_rerank_timeout_seconds: float = Field(
        default=8.0,
        ge=1.0,
        le=60.0,
        description="HTTP timeout for the tool-search LLM rerank call.",
    )
    agent_tool_search_llm_rerank_max_tokens: int = Field(
        default=256,
        ge=64,
        le=1024,
        description="max_tokens for the tool-search LLM rerank JSON response.",
    )
    agent_tool_search_llm_pre_denylist: list[str] = Field(
        default_factory=list,
        description=(
            "Tool names stripped from the LLM rerank candidate pool before the LLM call "
            "(defense-in-depth; high-risk tools without discovery/rules path are also excluded)."
        ),
    )
    agent_web_research_tools_enabled: bool = Field(
        default=False,
        description=(
            "When true, register ``web_search`` / ``web_fetch`` in the agent tool registry "
            "(academic host allowlist by default; see tool_manifest + web_research_tools)."
        ),
    )
    agent_doi_resolver_tool_enabled: bool = Field(
        default=False,
        description="When true, register ``doi_resolver`` bridge tool (OpenAlex + workspace match).",
    )
    agent_mcp_tools_enabled: bool = Field(
        default=False,
        description=(
            "When true, register MCP surface tools: ``call_mcp_tool``, ``list_mcp_resources``, "
            "``fetch_mcp_resource``, ``mcp_auth`` (see agent/tools/mcp_surface.py)."
        ),
    )
    agent_mcp_http_base_url: str | None = Field(
        default=None,
        description=(
            "Optional HTTP JSON-RPC base URL for MCP adapter. When unset, tools return "
            "``mcp_unconfigured`` without expanding scope into a full MCP manager."
        ),
    )
    agent_mcp_server_denylist: list[str] = Field(
        default_factory=list,
        description="Substring denylist for MCP ``server`` identifiers (policy deny-path).",
    )
    agent_mcp_request_timeout_seconds: float = Field(
        default=15.0,
        ge=1.0,
        le=120.0,
        description="HTTP timeout for MCP adapter JSON-RPC calls.",
    )
    agent_lsp_tool_enabled: bool = Field(
        default=False,
        description="When true, register bounded read-only ``lsp_tool`` (stdio JSON-RPC adapter).",
    )
    agent_lsp_server_argv: list[str] = Field(
        default_factory=list,
        description="Argv to spawn LSP server (stdio). Empty => ``lsp_unconfigured`` tool responses.",
    )
    agent_lsp_request_timeout_seconds: float = Field(
        default=5.0,
        ge=0.5,
        le=60.0,
        description="Per-LSP-request wall timeout (seconds).",
    )
    agent_lsp_max_result_items: int = Field(
        default=48,
        ge=1,
        le=256,
        description="Max symbol/reference items returned per ``lsp_tool`` call (payload budget).",
    )
    agent_runtime_monitor_tool_enabled: bool = Field(
        default=False,
        description="When true, register ``runtime_monitor_get`` for async task status snapshots.",
    )
    agent_runtime_monitor_max_error_tail_chars: int = Field(
        default=800,
        ge=64,
        le=8000,
        description="Max characters for ``error_tail`` in runtime monitor payloads.",
    )
    agent_research_plan_tool_enabled: bool = Field(
        default=False,
        description="When true, register ``research_plan_write`` (session_meta.research_plan + SSE).",
    )
    agent_ask_user_question_tool_enabled: bool = Field(
        default=False,
        description="When true, register ``ask_user_question`` (structured multi-choice + session pending).",
    )
    agent_brief_output_enabled: bool = Field(
        default=False,
        description="When true, register ``brief`` tool and surface ``run_metadata.brief`` (<=240 chars).",
    )
    agent_worktree_tools_enabled: bool = Field(
        default=False,
        description=(
            "When true, register bounded ``enter_worktree`` / ``exit_worktree`` session-scoped "
            "sandbox tools (Epic P1.1)."
        ),
    )
    agent_worktree_base_dir: str = Field(
        default=".agent_worktrees",
        description=(
            "Directory root for per-thread worktree sandboxes (repo-relative or absolute). "
            "Paths are validated to stay under this resolved root."
        ),
    )
    agent_plan_mode_tools_enabled: bool = Field(
        default=False,
        description=(
            "When true, register ``enter_plan_mode`` / ``exit_plan_mode`` session tools; "
            "high-risk tools are denied while plan_mode is active (Epic P2.3)."
        ),
    )
    agent_web_fetch_max_bytes: int = Field(
        default=524_288,
        ge=8_192,
        le=2_097_152,
        description="Max response bytes to read for ``web_fetch`` (safety cap).",
    )
    agent_web_fetch_cache_ttl_seconds: int = Field(
        default=600,
        ge=60,
        le=3600,
        description="In-process TTL seconds for ``web_fetch`` URL body cache.",
    )
    agent_web_search_http_timeout_seconds: float = Field(
        default=20.0,
        ge=5.0,
        le=120.0,
        description="HTTP timeout seconds for ``web_search`` Crossref ``/works`` GET.",
    )
    agent_web_fetch_http_timeout_seconds: float = Field(
        default=25.0,
        ge=5.0,
        le=120.0,
        description="HTTP timeout seconds for streamed ``web_fetch`` GET (includes TLS/TTFB).",
    )
    agent_tool_history_compact_enabled: bool = Field(
        default=False,
        description=(
            "When true, single-agent ReAct truncates older ToolMessage string payloads before "
            "each LLM hop (see tool_message_compact)."
        ),
    )
    agent_tool_history_compact_keep_latest_tool_messages: int = Field(
        default=4,
        ge=1,
        le=32,
        description="How many most recent tool results to leave uncompressed.",
    )
    agent_tool_history_compact_max_tool_chars: int = Field(
        default=6000,
        ge=400,
        le=100_000,
        description="Max characters retained per truncated ToolMessage body.",
    )
    agent_tool_message_microcompact_time_trigger_enabled: bool = Field(
        default=False,
        description=(
            "When true with agent_tool_history_compact_enabled, clear older ToolMessage bodies "
            "after a long client idle gap (see tool_message_compact)."
        ),
    )
    agent_tool_message_microcompact_time_gap_minutes: int = Field(
        default=10,
        ge=1,
        le=1440,
        description="Client idle gap (minutes) that triggers microcompact clearing of old tool rows.",
    )
    agent_tool_message_microcompact_keep_last_k_tool_results: int = Field(
        default=3,
        ge=1,
        le=32,
        description="How many most recent ToolMessage payloads to keep when microcompact triggers.",
    )
    agent_writer_verification_output_format_enabled: bool = Field(
        default=False,
        description=(
            "When true, writer specialist (normal mode) appends strict Scope/Result/Key sources/VERDICT "
            "layout instructions to the system prompt (verification-style contract)."
        ),
    )
    agent_post_compact_paper_sources_enabled: bool = Field(
        default=True,
        description=(
            "When true, persist compact paper refs after context_compacted and re-inject on the next "
            "turn via format_user_with_memory (see post_compact_attachments)."
        ),
    )
    agent_post_compact_paper_sources_max_items: int = Field(
        default=12,
        ge=1,
        le=48,
        description="Max paper source rows stored for post-compact restore.",
    )
    agent_pre_compact_sanitizers_enabled: bool = Field(
        default=True,
        description=(
            "Strip image parts and reinjected attachment blocks from messages/digests before "
            "compaction-related LLM calls (see message_sanitizers)."
        ),
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
    agent_note_enabled: bool = Field(
        default=False,
        description=(
            "Emit short LLM ``agent_note`` SSE events between routing decisions; "
            "costs extra tokens. Off by default; pilot only with explicit opt-in."
        ),
    )
    agent_note_max_per_turn: int = Field(
        default=2,
        ge=0,
        le=6,
        description="Hard cap of ``agent_note`` events per agent turn.",
    )
    agent_note_max_tokens: int = Field(
        default=64,
        ge=16,
        le=256,
        description="LLM ``max_tokens`` for a single ``agent_note`` generation.",
    )
    agent_note_timeout_seconds: float = Field(
        default=2.5,
        ge=0.5,
        le=10.0,
        description="Per-note timeout; on timeout the note is dropped silently.",
    )
    agent_note_model_id: str | None = Field(
        default=None,
        description="Override chat LLM model id for ``agent_note`` generation; defaults to effective chat model.",
    )
    agent_chat_max_retries: int = Field(
        default=1,
        ge=0,
        le=2,
        description=(
            "LangChain ChatOpenAI max_retries for agent chat / supervisor routing LLM calls "
            "(retries after failed HTTP). Lower reduces post-deadline tail load."
        ),
    )
    agent_classifier_max_retries: int = Field(
        default=0,
        ge=0,
        le=2,
        description="LangChain max_retries for turn-policy classifier LLM calls only.",
    )
    agent_graph_invoke_max_workers: int = Field(
        default=0,
        ge=0,
        le=32,
        description=(
            "ThreadPoolExecutor max_workers for sync LangGraph invoke with response deadline. "
            "0 = auto: min(16, max(4, (cpu_count or 2) * 2)). Non-zero overrides auto."
        ),
    )
    agent_min_llm_hop_reserve_seconds: float = Field(
        default=9.0,
        ge=1.0,
        le=120.0,
        description=(
            "Wall-clock reserve (seconds) before starting another agent LLM hop when the turn "
            "response deadline is almost exhausted (cooperative cutoff)."
        ),
    )
    agent_budget_stop_reasoning_enabled: bool = Field(
        default=True,
        description=(
            "Emit explicit budget stop reasons in debug_events/run_metadata when cooperative "
            "response-budget cutoff stops another LLM hop."
        ),
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
    agent_llm_full_history_compact_enabled: bool = Field(
        default=False,
        description=(
            "L4: when digest window is full (count >= agent_compaction_digest_cap), optionally "
            "call the chat LLM once per cooldown to replace rolling session_summary with a denser "
            "consolidation of all stored digests (audit in session_meta + context_compacted.audit)."
        ),
    )
    agent_llm_full_history_compact_cooldown_turns: int = Field(
        default=3,
        ge=1,
        le=50,
        description="Minimum turns between L4 LLM compactions while the digest window stays full.",
    )
    agent_llm_full_history_compact_max_digest_chars: int = Field(
        default=24_000,
        ge=4000,
        le=120_000,
        description="Max JSON chars fed into the L4 summarization prompt (truncated tail marked).",
    )
    agent_llm_full_history_compact_max_out_tokens: int = Field(
        default=2048,
        ge=256,
        le=8192,
        description="LLM max_tokens cap for L4 session consolidation output.",
    )

    agent_discovered_tools_carryover_enabled: bool = Field(
        default=True,
        description=(
            "Persist a rolling union of tool names seen in recent turns (CH4 digests) inside "
            "session capsules and bias rule-based tool shortlists to keep them across compaction."
        ),
    )
    agent_discovered_tools_carryover_max: int = Field(
        default=24,
        ge=4,
        le=64,
        description="Hard cap for stored discovered tool names in session memory.",
    )

    agent_thread_insights_enabled: bool = Field(
        default=False,
        description=(
            "Epic A (Train T1): after each turn with thread memory, refresh `session_meta.thread_insight` "
            "via chunked parallel summarization (deterministic stub summaries unless extended) and expose "
            "`run_metadata.thread_insight_audit` when `thread_id` is set."
        ),
    )
    agent_thread_insights_min_digests: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Minimum stored turn digests before emitting a thread_insight snapshot.",
    )
    agent_thread_insights_max_chunks: int = Field(
        default=4,
        ge=1,
        le=12,
        description="Upper bound on parallel chunk workers for thread_insights (uniform digest splits).",
    )
    agent_thread_insights_max_workers: int = Field(
        default=4,
        ge=1,
        le=8,
        description="ThreadPoolExecutor worker cap for thread_insights chunk summarization.",
    )
    agent_thread_insights_stale_after_turn_delta: int = Field(
        default=1,
        ge=1,
        le=50,
        description=(
            "Epic A1: refresh thread_insight when turn_counter advanced by at least this many "
            "turns since the snapshot's built_at_turn_counter (unless TTL/high-churn forces earlier)."
        ),
    )
    agent_thread_insights_ttl_seconds: int = Field(
        default=0,
        ge=0,
        le=2_592_000,
        description=(
            "Epic A1: mark insight stale after this many seconds since generated_at; 0 disables TTL."
        ),
    )
    agent_thread_insights_high_churn_window_digests: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Epic A1: count tool events across this many latest digests for high_churn detection.",
    )
    agent_thread_insights_high_churn_min_tool_events: int = Field(
        default=8,
        ge=1,
        le=128,
        description=(
            "Epic A1: if tool-use events in the churn window reach this threshold, force refresh "
            "with stale_reason=high_churn."
        ),
    )
    agent_thread_insights_max_consecutive_failures: int = Field(
        default=3,
        ge=1,
        le=20,
        description="Epic A1: open circuit-breaker after this many consecutive insight build failures.",
    )
    agent_thread_insights_circuit_open_skip_turns: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Epic A1: skip insight refresh for this many turns after circuit opens.",
    )
    agent_thread_insights_force_manual_stale: bool = Field(
        default=False,
        description="Epic A1 debug: treat every eligible turn as manual stale (tests / smoke).",
    )
    agent_thread_insights_llm_synthesis_enabled: bool = Field(
        default=False,
        description=(
            "Epic A1 / §10.2: when true, run a cache-instrumented side-LLM pass (forked_runtime) to "
            "synthesize thread_insight markdown from deterministic chunk summaries; requires API key. "
            "When false, insight text stays deterministic_stub and fork telemetry stays forked=false."
        ),
    )
    agent_thread_insights_llm_max_tokens: int = Field(
        default=768,
        ge=64,
        le=4096,
        description="Max output tokens for thread_insight LLM synthesis (forked_runtime path).",
    )
    agent_thread_insights_llm_temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Sampling temperature for thread_insight LLM synthesis.",
    )
    agent_thread_insights_incremental_enabled: bool = Field(
        default=True,
        description=(
            "When true, eligible thread_insight refreshes merge only new tail digests into the prior "
            "snapshot (deterministic stub or LLM incremental path) instead of re-chunking the full "
            "window; falls back to full rebuild when the digest window slides or fingerprints diverge."
        ),
    )
    agent_llm_full_history_compact_ptl_max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description=(
            "Epic A1: when L4 compaction LLM hits context/token limits, drop oldest digests and retry "
            "up to this many extra attempts (0 disables PTL retry for L4)."
        ),
    )

    agent_tool_search_message_discovery_enabled: bool = Field(
        default=True,
        description=(
            "Epic C0: merge tool names discovered in LangGraph message history (AIMessage.tool_calls / "
            "ToolMessage) into rule-based shortlists before session carry-over merge."
        ),
    )
    agent_tool_search_message_discovery_cap: int = Field(
        default=32,
        ge=0,
        le=128,
        description="Max tool names read from message history per shortlist call (chronological dedupe).",
    )
    agent_tool_search_strict_deferred_activation_enabled: bool = Field(
        default=False,
        description=(
            "Epic C0 Train T1: strict deferred activation (only-on-discovery). When true with rule "
            "tool_search, tools with ``ToolManifestEntry.strict_deferred_requires_discovery`` stay "
            "bound only if rule-scored, merged from LangGraph message history, session carry-over, "
            "or retrieval core baseline (workspace_inspect/paper_profile/find_works); optional "
            "baseline extras (idea_search, paper_quote_search) are not auto-injected without those "
            "paths. Low-signal / fallback_full still return full catalog (policy relaxed for the turn)."
        ),
    )

    agent_away_summary_enabled: bool = Field(
        default=True,
        description=(
            "When true and the client reports a long idle gap, inject a short deterministic "
            "`<away_recap>` block ahead of `<session_memory>`."
        ),
    )
    agent_away_summary_client_idle_ms_threshold: int = Field(
        default=900_000,
        ge=60_000,
        le=86_400_000,
        description="Minimum client-reported idle milliseconds before away recap is injected.",
    )

    agent_allowed_tools_matrix_enabled: bool = Field(
        default=False,
        description=(
            "Optional defense-in-depth filtering of bound tools by agent_runtime/specialist role "
            "and coordinator tool_policy (see agent.tool_execution_pipeline)."
        ),
    )
    agent_tool_denylist_always: list[str] = Field(
        default_factory=list,
        description="Strip these tool names from every bound tool surface when the matrix is enabled.",
    )
    agent_tool_denylist_by_mode: dict[str, list[str]] = Field(
        default_factory=dict,
        description=(
            "Per-mode denylist keyed by tool_execution_pipeline.effective_mode_key, e.g. "
            "`supervisor:graph_agent` or `single_agent_react`."
        ),
    )
    agent_tool_allowlist_by_tool_policy: dict[str, list[str]] = Field(
        default_factory=dict,
        description=(
            "Optional allowlists keyed by coordinator tool_policy (`no_tools`, `clarify`, "
            "`allow_tools`). When a key is present and non-empty, only listed tools may remain bound."
        ),
    )

    agent_sidechain_transcripts_enabled: bool = Field(
        default=True,
        description="Append JSONL sidechain transcripts for specialist ReAct branches (debug/recovery).",
    )
    agent_sidechain_transcripts_dir: str = Field(
        default=".agent_sidechains",
        description=(
            "Directory (repo-relative or absolute) for JSONL sidechain logs. "
            "Must be writable by the API process; in Docker bind-mounts use e.g. `/tmp/...` or "
            "set ``SCIENCE_GRAPHRAG_AGENT_SIDECHAIN_TRANSCRIPTS_ENABLED=0`` (see "
            "``docker-compose.live-check.yml`` / ``scripts/live_check/README.md``)."
        ),
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

    base_settings = Settings()
    service = SettingsService(repo_root=Path(__file__).resolve().parents[1])
    return service.build_runtime_settings(base_settings)
