from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


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


class WorkIdsBatchBody(BaseModel):
    work_ids: list[str] = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Work node ids to resolve (deduped server-side; cap 2000 per request).",
    )


class WorkSummaryBatchResponse(BaseModel):
    items: list[dict[str, Any]]
