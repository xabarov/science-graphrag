"""Shared runtime envelope for claims extraction calls."""

from __future__ import annotations

from dataclasses import dataclass

from science_graphrag.config import Settings
from science_graphrag.ingestion.llm.extractor import EXTRACT_MAYBE_MAX_INNER_ATTEMPTS
from science_graphrag.ingestion.llm.extractor_factory import (
    IngestionExtractorPreset,
    build_ingestion_extractor,
)
from science_graphrag.utils.llm_deadline import MonotonicDeadline


@dataclass(frozen=True, slots=True)
class ClaimsRuntime:
    """Resolved claims extraction runtime parameters and dependencies."""

    extractor: object
    payload_max_chars: int
    transport_timeout_seconds: float
    operation_budget_seconds: float
    operation_deadline: MonotonicDeadline


def build_claims_runtime(settings: Settings, *, force_benchmark: bool) -> ClaimsRuntime:
    """Build claims runtime with the default extractor builder."""

    return _build_claims_runtime_with_builder(
        settings,
        force_benchmark=force_benchmark,
        extractor_builder=build_ingestion_extractor,
    )


def _build_claims_runtime_with_builder(
    settings: Settings,
    *,
    force_benchmark: bool,
    extractor_builder,
) -> ClaimsRuntime:
    """Build claims runtime with an injectable extractor builder for tests."""

    preset = (
        IngestionExtractorPreset.CLAIMS_BENCHMARK
        if force_benchmark
        else IngestionExtractorPreset.CLAIMS
    )
    extractor = extractor_builder(settings, preset)
    transport = float(settings.extraction_llm_timeout_seconds)
    operation_budget = min(
        1200.0,
        max(
            transport * 4.0,
            transport * float(EXTRACT_MAYBE_MAX_INNER_ATTEMPTS) * 4.0,
        ),
    )
    deadline = MonotonicDeadline.from_budget_seconds(operation_budget)
    return ClaimsRuntime(
        extractor=extractor,
        payload_max_chars=26_000 if force_benchmark else 28_000,
        transport_timeout_seconds=transport,
        operation_budget_seconds=operation_budget,
        operation_deadline=deadline,
    )
