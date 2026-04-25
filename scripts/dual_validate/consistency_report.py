"""Schema + IO for the dual-validate consistency report.

A consistency report is written next to the pack as ``consistency_report.json``
and links extractor A (the existing gold) with extractor B (the independent LLM run).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CONSISTENCY_REPORT_SCHEMA_VERSION = 1


@dataclass
class ExtractorInfo:
    """Provenance for one side of the comparison (A or B)."""

    role: str
    source: str
    count: int
    model: str | None = None
    base_url: str | None = None
    prompt_hash: str | None = None
    raw_response_path: str | None = None
    usage_tokens: dict[str, int] | None = None
    latency_ms: int | None = None


@dataclass
class ConsistencyReport:
    """Top-level schema-v1 report. Persisted next to the pack."""

    pack_id: str
    pack_path: str
    layer: str
    extractor_a: ExtractorInfo
    extractor_b: ExtractorInfo
    matched_pairs: list[dict[str, Any]]
    unmatched_a: list[dict[str, Any]]
    unmatched_b: list[dict[str, Any]]
    summary: dict[str, Any]
    spot_check_priority: str
    spot_check_priority_rationale: str
    schema_version: int = CONSISTENCY_REPORT_SCHEMA_VERSION
    generated_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Plain-dict export with ``schema_version`` first for human review."""

        d = asdict(self)
        ordered: dict[str, Any] = {
            "schema_version": d.pop("schema_version"),
            "pack_id": d.pop("pack_id"),
            "pack_path": d.pop("pack_path"),
            "layer": d.pop("layer"),
            "generated_at_utc": d.pop("generated_at_utc"),
            "spot_check_priority": d.pop("spot_check_priority"),
            "spot_check_priority_rationale": d.pop("spot_check_priority_rationale"),
            "extractor_a": d.pop("extractor_a"),
            "extractor_b": d.pop("extractor_b"),
            "summary": d.pop("summary"),
            "matched_pairs": d.pop("matched_pairs"),
            "unmatched_a": d.pop("unmatched_a"),
            "unmatched_b": d.pop("unmatched_b"),
        }
        return ordered


def write_report(report: ConsistencyReport, path: Path) -> None:
    """Persist as pretty-printed UTF-8 JSON with trailing newline."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def validate_report_dict(d: dict[str, Any]) -> list[str]:
    """Return a list of human-readable validation errors (empty list = OK).

    Lightweight assertions chosen for self-documentation in tests; do not replace JSON
    Schema validation in CI (see ``tests/eval/test_gold_schemas.py`` for that path).
    """

    errors: list[str] = []
    required_top = (
        "schema_version",
        "pack_id",
        "pack_path",
        "layer",
        "generated_at_utc",
        "spot_check_priority",
        "spot_check_priority_rationale",
        "extractor_a",
        "extractor_b",
        "summary",
        "matched_pairs",
        "unmatched_a",
        "unmatched_b",
    )
    for k in required_top:
        if k not in d:
            errors.append(f"missing top-level field: {k}")
    if d.get("schema_version") != CONSISTENCY_REPORT_SCHEMA_VERSION:
        errors.append(f"schema_version != {CONSISTENCY_REPORT_SCHEMA_VERSION}")
    if d.get("spot_check_priority") not in {"low", "medium", "high"}:
        errors.append("spot_check_priority must be one of low/medium/high")
    for side in ("extractor_a", "extractor_b"):
        info = d.get(side, {})
        for k in ("role", "source", "count"):
            if k not in info:
                errors.append(f"{side} missing field: {k}")
    return errors
