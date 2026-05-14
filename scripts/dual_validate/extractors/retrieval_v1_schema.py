"""Pydantic response shapes for ``retrieval_v1`` dual-validate extractors."""

from __future__ import annotations

from pydantic import BaseModel, Field


class WorkspaceScopedResponseModel(BaseModel):
    expected_corpus_work_ids: list[str] = Field(default_factory=list)
    would_violate_workspace_with: list[str] = Field(default_factory=list)
    rationale: str = Field(default="")


class HybridAblationResponseModel(BaseModel):
    relevant_corpus_work_ids: list[str] = Field(default_factory=list)
    irrelevant_corpus_work_ids: list[str] = Field(default_factory=list)
    rationale: str = Field(default="")


class MultihopResponseModel(BaseModel):
    expected_chain_corpus_work_ids: list[str] = Field(default_factory=list)
    expected_node_canonical_names: list[str] = Field(default_factory=list)
    rationale: str = Field(default="")


__all__ = [
    "HybridAblationResponseModel",
    "MultihopResponseModel",
    "WorkspaceScopedResponseModel",
]
