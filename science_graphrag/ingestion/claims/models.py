"""Datatypes for claims / evidence extraction (Wave O)."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Literal

ClaimType = Literal["performance", "method", "comparison", "mechanism", "limitation"]
Polarity = Literal["positive", "negative", "neutral"]

CLAIM_TYPES: frozenset[str] = frozenset(
    {"performance", "method", "comparison", "mechanism", "limitation"},
)
POLARITIES: frozenset[str] = frozenset({"positive", "negative", "neutral"})


def normalize_claim_text_for_id(text: str) -> str:
    return " ".join(str(text or "").lower().split())


def stable_claim_id(work_id: str, normalized_text: str) -> str:
    key = f"claim:{work_id}:{normalized_text[:500]}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))


def stable_evidence_id(claim_id: str, chunk_fingerprint: str, quote: str) -> str:
    q = re.sub(r"\s+", " ", str(quote or "").strip())[:200]
    key = f"evidence:{claim_id}:{chunk_fingerprint}:{q}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))


def coerce_claim_type(raw: str | None) -> ClaimType:
    s = str(raw or "").strip().lower().replace("-", "_")
    mapping = {
        "perf": "performance",
        "performance_claim": "performance",
        "methods": "method",
        "compare": "comparison",
        "comparing": "comparison",
        "mechanistic": "mechanism",
        "limit": "limitation",
        "limits": "limitation",
    }
    s = mapping.get(s, s)
    if s in CLAIM_TYPES:
        return s  # type: ignore[return-value]
    return "mechanism"


def coerce_polarity(raw: str | None) -> Polarity:
    s = str(raw or "").strip().lower()
    if s in POLARITIES:
        return s  # type: ignore[return-value]
    return "neutral"


@dataclass
class EvidenceDraft:
    evidence_id: str
    chunk_fingerprint: str
    quote: str
    section_path: str | None = None


@dataclass
class ClaimDraft:
    claim_id: str
    text: str
    normalized_text: str
    claim_type: ClaimType
    polarity: Polarity
    confidence: float
    evidence: list[EvidenceDraft] = field(default_factory=list)
