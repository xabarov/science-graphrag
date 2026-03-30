"""Stable Author node ids for cross-work canonicalization."""

from __future__ import annotations

import re
import uuid


def canonical_author_node_id(raw_name: str) -> str:
    """
    Deterministic :Author id from a display name (lowercased, whitespace-normalized).

    Same spelling across different :Work nodes maps to one author vertex; different
    spellings remain distinct (MVP — ORCID wiring can refine this later).
    """

    normalized = re.sub(r"\s+", " ", (raw_name or "").strip().lower())
    if not normalized:
        normalized = "unknown"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "author:" + normalized))
