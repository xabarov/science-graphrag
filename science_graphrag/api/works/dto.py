from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class WorkListResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int


class ClaimEvidenceOut(BaseModel):
    chunk_fingerprint: str
    quote: str
    section_path: str | None = None


class ClaimOut(BaseModel):
    claim_id: str
    normalized_text: str
    claim_type: str
    polarity: str
    confidence: float
    evidence: list[ClaimEvidenceOut]


class WorkClaimsResponse(BaseModel):
    work_id: str
    items: list[ClaimOut]
