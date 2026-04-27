"""Factory for ``SyncInstructorExtractor`` presets used by production ingestion."""

from __future__ import annotations

from enum import Enum

from science_graphrag.config import Settings
from science_graphrag.ingestion.llm.extractor import SyncInstructorExtractor


class IngestionExtractorPreset(str, Enum):
    """Which ingestion stage is requesting an extractor (token/temperature presets differ)."""

    METADATA = "metadata"
    REFERENCES = "references"
    SEMANTIC = "semantic"
    CLAIMS = "claims"
    CLAIMS_BENCHMARK = "claims_benchmark"


def build_ingestion_extractor(
    settings: Settings,
    preset: IngestionExtractorPreset,
) -> SyncInstructorExtractor:
    """
    Centralize OpenAI-compatible client wiring for ingestion structured extraction.

    Stage-specific ``max_tokens`` / ``temperature`` remain explicit per preset.
    """

    api_key = (settings.extraction_llm_api_key or "").strip()
    if not api_key:
        msg = "extraction_llm_api_key is required to build ingestion extractor"
        raise ValueError(msg)

    base_url = settings.extraction_llm_base_url
    model = settings.extraction_llm_model
    mode = settings.extraction_llm_mode
    timeout_seconds = float(settings.extraction_llm_timeout_seconds)

    if preset == IngestionExtractorPreset.METADATA:
        max_tokens = int(settings.extraction_llm_max_tokens_metadata)
        temperature = float(settings.extraction_llm_temperature)
    elif preset == IngestionExtractorPreset.REFERENCES:
        max_tokens = int(settings.extraction_llm_max_tokens_references)
        temperature = float(settings.extraction_llm_temperature)
    elif preset == IngestionExtractorPreset.SEMANTIC:
        max_tokens = int(settings.semantic_extraction_max_tokens)
        temperature = float(settings.semantic_extraction_temperature)
    elif preset == IngestionExtractorPreset.CLAIMS_BENCHMARK:
        cap = 16384
        max_tokens = min(int(settings.claims_extraction_max_tokens), cap)
        temperature = float(settings.extraction_llm_temperature)
    else:
        # Match CLAIMS_BENCHMARK cap so production ingest can use full Settings range up to 16k.
        cap = 16384
        max_tokens = min(int(settings.claims_extraction_max_tokens), cap)
        temperature = float(settings.extraction_llm_temperature)

    return SyncInstructorExtractor(
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout_seconds=timeout_seconds,
        mode=mode,
    )
