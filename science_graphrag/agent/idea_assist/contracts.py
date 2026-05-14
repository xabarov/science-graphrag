from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

IdeaAssistMode = Literal["hypotheses", "contradictions", "both"]


@dataclass
class HypothesisCandidate:
    text: str
    supporting_claim_ids: list[str]
    novelty_hint: str
    evidence_quotes: list[str]


@dataclass
class ContradictionPair:
    claim_a_id: str
    claim_b_id: str
    description: str


@dataclass
class IdeaWorkflowOutput:
    hypotheses: list[HypothesisCandidate]
    contradictions: list[ContradictionPair]
    tool_trace: list
    duration_ms: int


class HypothesisLLM(BaseModel):
    text: str = Field(default="", max_length=1000)
    supporting_claim_ids: list[str] = Field(default_factory=list)
    novelty_hint: str = Field(default="", max_length=600)
    evidence_quotes: list[str] = Field(default_factory=list)


class ContradictionLLM(BaseModel):
    claim_a_id: str = Field(default="", max_length=200)
    claim_b_id: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=600)


class IdeaAssistLLMResponse(BaseModel):
    hypotheses: list[HypothesisLLM] = Field(default_factory=list)
    contradictions: list[ContradictionLLM] = Field(default_factory=list)


IDEA_ASSIST_SYSTEM = """You are an idea-assist engine for scientific workspaces.

Generate up to 3 hypothesis candidates and/or contradiction pairs from grounded claim evidence.

Rules:
1) Return strict JSON only.
2) Every hypothesis must cite claim IDs and include at least one verbatim evidence quote.
3) Avoid plagiarizing titles/abstracts; provide a novelty hint.
4) For contradictions, only emit pairs with explicit polarity or claim-text conflict evidence.
5) If evidence is insufficient, return empty arrays.
"""
