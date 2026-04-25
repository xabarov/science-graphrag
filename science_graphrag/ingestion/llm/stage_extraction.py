"""Compatibility facade for split stage extraction modules."""

from science_graphrag.ingestion.llm.diagnostics import ExtractionDiagnostics
from science_graphrag.ingestion.llm.heuristics.chunking import (
    reference_chunk_groups as _reference_chunk_groups,
)
from science_graphrag.ingestion.llm.heuristics.chunking import reference_chunks as _reference_chunks
from science_graphrag.ingestion.llm.heuristics.metadata import (
    canonicalize_arxiv_id as _canonicalize_arxiv_id,
)
from science_graphrag.ingestion.llm.heuristics.references import (
    merge_reference_sets as _merge_reference_sets,
)
from science_graphrag.ingestion.llm.heuristics.references import (
    normalize_raw_reference_key as _normalize_raw_reference_key,
)
from science_graphrag.ingestion.llm.heuristics.references import (
    references_from_llm as _references_from_llm,
)
from science_graphrag.ingestion.llm.orchestrator import extract_stages_llm_first
from science_graphrag.ingestion.llm.prompts.metadata import (
    SYSTEM_FENCE,
    SYSTEM_META_NORMALIZE,
    extraction_layer1_prompt_fingerprint,
)

__all__ = [
    "SYSTEM_FENCE",
    "SYSTEM_META_NORMALIZE",
    "ExtractionDiagnostics",
    "_canonicalize_arxiv_id",
    "_merge_reference_sets",
    "_normalize_raw_reference_key",
    "_reference_chunk_groups",
    "_reference_chunks",
    "_references_from_llm",
    "extract_stages_llm_first",
    "extraction_layer1_prompt_fingerprint",
]
