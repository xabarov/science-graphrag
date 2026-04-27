"""S3/MinIO object key helpers for Phase 3 benchmark runs and diagnostics (roadmap §7.2)."""

from __future__ import annotations

import re


def _safe_segment(value: str, *, fallback: str = "unknown") -> str:
    """Restrict path segments to reduce key injection / odd URL issues."""
    s = (value or "").strip()
    if not s:
        return fallback
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", s)
    return cleaned[:256] or fallback


DEFAULT_BENCHMARK_RUNS_PREFIX = "science-benchmarks"
DEFAULT_DIAGNOSTICS_PREFIX = "science-diagnostics"


def benchmark_run_full_object_key(
    run_id: str, *, prefix: str = DEFAULT_BENCHMARK_RUNS_PREFIX
) -> str:
    """Full UI/API benchmark run JSON (``runs/<run_id>/full.json``)."""
    rid = _safe_segment(run_id, fallback="run")
    base = prefix.strip().strip("/")
    return f"{base}/runs/{rid}/full.json"


def chat_agent_case_result_object_key(
    run_id: str,
    case_id: str,
    *,
    prefix: str = DEFAULT_BENCHMARK_RUNS_PREFIX,
    suffix: str = "case_result.json",
) -> str:
    """Per-case heavy payload under chat-agent namespace (reserved for future trace uploads)."""
    r = _safe_segment(run_id, fallback="run")
    c = _safe_segment(case_id, fallback="case")
    base = prefix.strip().strip("/")
    return f"{base}/chat-agent/{r}/cases/{c}/{suffix}"


def od_diagnostics_object_key(
    stem: str,
    *,
    prefix: str = DEFAULT_DIAGNOSTICS_PREFIX,
    subdir: str = "od",
) -> str:
    """OD manifest / audit / backfill objects under ``science-diagnostics/od/...``."""
    raw = (stem or "").strip().replace("\\", "/")
    leaf = raw.rsplit("/", maxsplit=1)[-1]
    st = re.sub(r"[^a-zA-Z0-9._-]+", "_", leaf).strip("._") or "artifact"
    st = st[:512]
    sub = _safe_segment(subdir, fallback="od")
    base = prefix.strip().strip("/")
    return f"{base}/{sub}/{st}"
