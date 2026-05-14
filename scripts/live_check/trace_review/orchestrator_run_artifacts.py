"""Trace-review artifact assembly: thin facade over ``artifact_pipeline``."""

from __future__ import annotations

from .artifact_pipeline import run_trace_review_artifact_phases_after_http_e2e

__all__ = ["run_trace_review_artifact_phases_after_http_e2e"]
