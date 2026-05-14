"""JSON/Markdown writes and trace-review artifact merge helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .orchestrator_report import json_safe_value as _json_safe_value
from .orchestrator_report import (
    patch_run_context_execution_diagnostics as _patch_run_context_execution_diagnostics,
)
from .orchestrator_report import write_markdown as _write_markdown


def write_trace_review_json(path: Path, review_dict: dict[str, Any]) -> None:
    """Write trace-review JSON with stable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_json_safe_value(review_dict), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_trace_review_markdown(path: Path, review_dict: dict[str, Any]) -> None:
    """Write trace-review Markdown summary."""
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_markdown(path, review_dict)


def write_trace_review_outputs(
    out_json: Path,
    out_md: Path,
    review_dict: dict[str, Any],
) -> None:
    """Persist JSON + Markdown for a trace-review run."""
    write_trace_review_json(out_json, review_dict)
    write_trace_review_markdown(out_md, review_dict)


def apply_acceptance_summary_if_enabled(
    review_dict: dict[str, Any],
    *,
    enabled: bool,
    build_acceptance_summary: Callable[[dict[str, Any]], Any],
) -> None:
    """Mutate ``review_dict`` with acceptance summary when enabled."""
    if enabled:
        review_dict["acceptance_summary"] = build_acceptance_summary(review_dict)


def merge_compaction_into_review_file(  # pylint: disable=too-many-arguments
    merge_target: Path,
    compaction_meta: dict[str, Any],
    *,
    primary_out_json: Path,
    out_md: Path,
    fallback_review_dict: dict[str, Any],
    exec_stages: list[dict[str, Any]],
    hb_sec: float,
    e2e_subprocess_timeout_sec: float | int,
    with_acceptance_summary: bool,
    build_acceptance_summary: Callable[[dict[str, Any]], Any],
) -> dict[str, Any]:
    """Inject ``compaction_turn_review`` into ``merge_target`` JSON and refresh MD.

    On parse/write failure, patch ``fallback_review_dict`` and write ``primary_out_json``
    (matches legacy behavior when ``merge_target`` is not the primary artifact path).
    """
    if not merge_target.exists():
        return fallback_review_dict

    try:
        merged = json.loads(merge_target.read_text(encoding="utf-8"))
        merged["compaction_turn_review"] = compaction_meta
        _patch_run_context_execution_diagnostics(
            merged,
            exec_stages=exec_stages,
            hb_sec=hb_sec,
            e2e_subprocess_timeout_sec=e2e_subprocess_timeout_sec,
        )
        merge_target.write_text(
            json.dumps(_json_safe_value(merged), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        review_dict = merged
        apply_acceptance_summary_if_enabled(
            review_dict,
            enabled=with_acceptance_summary,
            build_acceptance_summary=build_acceptance_summary,
        )
        write_trace_review_markdown(out_md, review_dict)
        return review_dict
    except (OSError, json.JSONDecodeError):
        fallback_review_dict["compaction_turn_review"] = compaction_meta
        _patch_run_context_execution_diagnostics(
            fallback_review_dict,
            exec_stages=exec_stages,
            hb_sec=hb_sec,
            e2e_subprocess_timeout_sec=e2e_subprocess_timeout_sec,
        )
        apply_acceptance_summary_if_enabled(
            fallback_review_dict,
            enabled=with_acceptance_summary,
            build_acceptance_summary=build_acceptance_summary,
        )
        write_trace_review_json(primary_out_json, fallback_review_dict)
        write_trace_review_markdown(out_md, fallback_review_dict)
        return fallback_review_dict


__all__ = [
    "apply_acceptance_summary_if_enabled",
    "merge_compaction_into_review_file",
    "write_trace_review_json",
    "write_trace_review_markdown",
    "write_trace_review_outputs",
]
