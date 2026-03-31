"""Gold spec for semantic Method/Dataset extraction."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class SemanticGoldSpec(BaseModel):
    case_id: str
    schema_version: int = 1
    description: str | None = None
    article_path: str | None = Field(
        default=None,
        description="Optional path relative to case dir for article.md (default: article.md)",
    )
    min_method_names: int = Field(default=0, ge=0)
    max_method_names: int | None = Field(default=None)
    min_method_recall_ratio: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional lower bound for method recall (tp / |gold methods|) when LLM is enabled.",
    )
    min_dataset_recall_ratio: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional lower bound for dataset recall (tp / |gold datasets|) when LLM is enabled.",
    )
    expected_method_names_normalized: list[str] = Field(default_factory=list)
    expected_dataset_names_normalized: list[str] = Field(default_factory=list)
    allow_empty_when_no_llm: bool = Field(
        default=True,
        description="If true, empty predictions pass when extraction_llm is disabled.",
    )

    @staticmethod
    def load(path: Path) -> "SemanticGoldSpec":
        return SemanticGoldSpec.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def model_dump_for_report(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
