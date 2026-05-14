"""Pydantic models for benchmark HTTP API responses and bodies."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CaseListItem(BaseModel):
    """One row in the benchmark cases list (layer-1, layer-2, or graph-v1 catalog)."""

    case_id: str
    family: str = "layer1"
    tier: str | None = None
    has_article_md: int
    has_gold_json: int
    has_semantic_gold: int = 0
    has_graph_expectations: int = 0


class CasesListResponse(BaseModel):
    """Response payload for GET /benchmark/cases."""

    items: list[CaseListItem]
    total: int


class CaseDetailResponse(BaseModel):
    """Response payload for GET /benchmark/cases/{case_id}."""

    case_id: str
    tier: str | None = None
    article_md: str
    article_sections: list[dict[str, Any]] = Field(default_factory=list)
    gold: dict[str, Any]
    artifacts: dict[str, Any] = Field(default_factory=dict)


class CaseArtifactArticle(BaseModel):
    """Article file pointer for a benchmark case."""

    path_relative_to_repo: str | None = None
    present: bool


class CaseGoldVariant(BaseModel):
    """One gold file variant (e.g. curated vs teacher)."""

    id: str
    filename: str
    path_relative_to_repo: str | None = None
    present: bool


class CaseSemanticGoldRef(BaseModel):
    """Layer-2 semantic gold file presence."""

    present: bool
    path_relative_to_repo: str | None = None


class CaseArtifactsResponse(BaseModel):
    """Response payload for GET /benchmark/cases/{case_id}/artifacts."""

    case_id: str
    family: str
    fixture_dir_relative: str | None = None
    article: CaseArtifactArticle
    gold_variants: list[CaseGoldVariant] = Field(default_factory=list)
    semantic_gold: CaseSemanticGoldRef | None = None
    semantic_gold_teacher: CaseSemanticGoldRef | None = None
    graph_expectations: bool = False
    last_run_hints: dict[str, Any] | None = None


class RunCreateRequest(BaseModel):
    """Request payload for POST /benchmark/runs."""

    case_ids: list[str] | str = Field(
        ..., description='Either a list of case_ids, or "all" / "merge_safe".'
    )
    label: str | None = None
    family: str = Field(default="layer1", description='Benchmark family: "layer1" or "layer2".')
    model_profile: str | None = None
    model_id: str | None = None
    base_url_override: str | None = None
    api_key_env_name: str | None = None
    gold_source: str | None = None
    threshold_profile: str | None = None


class RunCreateResponse(BaseModel):
    """Response payload for POST /benchmark/runs."""

    run_id: str
    status: str
    benchmark_family: str = "layer1"
    label: str | None = None
    run_config: dict[str, Any] = Field(default_factory=dict)


class RunListItem(BaseModel):
    """One row in the runs list."""

    run_id: str
    benchmark_family: str = "layer1"
    label: str | None = None
    status: str
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    run_config: dict[str, Any] = Field(default_factory=dict)
    progress: dict[str, Any]
    summary: dict[str, Any]


class RunsListResponse(BaseModel):
    """Response payload for GET /benchmark/runs."""

    items: list[RunListItem]
    total: int


class RunDetailResponse(BaseModel):
    # We intentionally keep it untyped to allow evolution of metrics/predicted payloads.
    """Response payload for GET /benchmark/runs/{run_id}."""

    data: dict[str, Any]


class RunSummaryResponse(BaseModel):
    """Response payload for GET /benchmark/runs/{run_id}/summary (no per-case result blobs)."""

    data: dict[str, Any]


class RunsCompareResponse(BaseModel):
    """Response payload for GET /benchmark/runs/compare."""

    data: dict[str, Any]


class RunCasesListResponse(BaseModel):
    """Response payload for GET /benchmark/runs/{run_id}/cases (paginated slim rows)."""

    data: dict[str, Any]


class RunCaseDetailResponse(BaseModel):
    """Response payload for GET /benchmark/runs/{run_id}/cases/{case_id}."""

    data: dict[str, Any]


class GraphSnapshotPreviewResponse(BaseModel):
    """Response payload for POST /benchmark/cases/{case_id}/graph-snapshot-preview."""

    data: dict[str, Any]


class BenchmarkModelProfileResponse(BaseModel):
    """One model preset available to the benchmark launcher."""

    profile_id: str
    label: str
    role: str
    family_support: list[str]
    model_id: str | None = None
    default_gold_source: str | None = None
    default_threshold_profile: str | None = None
    supports_custom_model_id: bool = False


class BenchmarkModelsResponse(BaseModel):
    """Response payload for GET /benchmark/models."""

    items: list[BenchmarkModelProfileResponse]
    total: int
