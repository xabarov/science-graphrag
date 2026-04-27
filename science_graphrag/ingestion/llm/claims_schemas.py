"""Pydantic response schemas for LLM-backed claims extraction (shared with eval/tests)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EvidenceLLM(BaseModel):
    """Evidence line item in full (non-benchmark) claims schema."""
    chunk_fingerprint: str = Field(
        default="",
        max_length=512,
        description="Exact chunk_fingerprint value from the CHUNK header above.",
    )
    quote: str = Field(
        default="",
        max_length=4000,
        description="Verbatim substring copied from the chunk text — must match exactly.",
    )
    section_path: str | None = Field(default=None, max_length=512)


class ClaimLLM(BaseModel):
    """Single claim in full (non-benchmark) claims schema."""
    claim_text: str = Field(
        default="",
        max_length=2000,
        description=(
            "Required. A concise scientific assertion in plain English "
            "(15–300 chars). Summarise WHAT the paper claims, not WHERE it says it."
        ),
    )
    claim_type: str = Field(default="mechanism", max_length=64)
    polarity: str = Field(default="neutral", max_length=32)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    evidence: list[EvidenceLLM] = Field(
        default_factory=list,
        description="One or more verbatim quotes from the chunks that support the claim.",
    )


class ClaimsLLMResponse(BaseModel):
    """Full production claims LLM response wrapper."""
    claims: list[ClaimLLM] = Field(default_factory=list)


class EvidenceLLMBenchmark(BaseModel):
    """Evidence row for benchmark / compact claims schema."""
    chunk_fingerprint: str = Field(
        default="",
        max_length=512,
        description="Exact chunk_fingerprint value from the CHUNK header above.",
    )
    quote: str = Field(
        default="",
        max_length=480,
        description="Verbatim substring from chunk text; keep ≤480 chars (benchmark cap).",
    )
    section_path: str | None = Field(default=None, max_length=512)


class ClaimLLMBenchmark(BaseModel):
    """Single claim for benchmark / compact schema (one evidence)."""
    claim_text: str = Field(
        default="",
        max_length=400,
        description="Concise scientific assertion (benchmark: ≤400 chars).",
    )
    claim_type: str = Field(default="mechanism", max_length=64)
    polarity: str = Field(default="neutral", max_length=32)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    evidence: list[EvidenceLLMBenchmark] = Field(
        default_factory=list,
        min_length=1,
        max_length=1,
        description="Exactly one evidence row with a verbatim quote.",
    )


class ClaimsLLMResponseBenchmark(BaseModel):
    """Benchmark / compact-fallback claims LLM response wrapper."""
    claims: list[ClaimLLMBenchmark] = Field(
        default_factory=list,
        max_length=28,
        description="At most 28 claims; keeps tool JSON small for eval/BT6.",
    )
