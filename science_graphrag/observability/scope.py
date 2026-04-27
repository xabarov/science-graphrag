from __future__ import annotations

import os

_PHOENIX_TRACE_SCOPE_FULL = "full"
_PHOENIX_TRACE_SCOPE_EXTRACTION_LLM = "extraction_llm"

_EXTRACTION_LLM_CHAIN_NAMES = frozenset(
    {
        "ingest_document",
        "ingest.extract_meta.metadata_and_refs",
        # Claims stage parent (child ``llm.claims_extraction`` is allowlisted separately).
        "ingest.extract_claims.llm",
    }
)
_EXTRACTION_LLM_MANUAL_LLM_NAMES = frozenset(
    {
        "llm.metadata_extraction",
        "llm.authorships_extraction",
        "llm.references_extraction",
        "llm.semantic_method_dataset",
        "llm.claims_extraction",
        "llm.claims_extraction_compact",
        "llm.vl_pdf",
    }
)


def phoenix_trace_scope() -> str:
    """OTel/Phoenix verbosity: ``full`` (default) or ``extraction_llm``.

    With ``extraction_llm``, ingest allowlisted CHAIN/LLM spans are recorded, and **product
    agent** spans whose names start with ``agent.`` / ``llm.agent.`` / ``retrieval.qdrant.``
    are also recorded so ``phoenix_trace_id`` stays usable for ``/v2/agent/query`` without
    switching the whole process to ``full``.
    """

    return os.getenv("PHOENIX_TRACE_SCOPE", _PHOENIX_TRACE_SCOPE_FULL).strip().lower()


PHOENIX_TRACE_SCOPE = phoenix_trace_scope()


def is_extraction_llm_scope() -> bool:
    return phoenix_trace_scope() == _PHOENIX_TRACE_SCOPE_EXTRACTION_LLM
