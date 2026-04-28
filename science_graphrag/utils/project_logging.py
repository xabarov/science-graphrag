"""
Project-wide logging for ingestion and LLM extraction.

Stdlib logging only. Levels:

- ``SCIENCE_GRAPHRAG_LOG_LEVEL`` — logger ``science_graphrag`` (default ``INFO``).
- ``SCIENCE_GRAPHRAG_HTTP_LOG_LEVEL`` — ``httpx``, ``httpcore``, ``urllib3``
  (default ``WARNING``) to reduce per-request noise during VL / API calls.
- ``SCIENCE_GRAPHRAG_DRAMATIQ_LOG_LEVEL`` — logger ``dramatiq`` (default ``WARNING``)
  to reduce per-process worker boot noise.
- ``SCIENCE_GRAPHRAG_LOG_FORMAT`` — ``text`` (default) or ``json`` (one JSON object
  per stderr line).
- ``SCIENCE_GRAPHRAG_LOG_LEVEL_INGEST`` — optional level for logger subtree
  ``science_graphrag.ingestion`` only (unset = inherit ``SCIENCE_GRAPHRAG_LOG_LEVEL``).

Correlation: when ``ingest_log_context`` is active (see ``log_context``), stderr
lines from the ``science_graphrag`` handler include ``job_id`` and ``workspace_id``.

**Explicit ``extra=``** (when context is missing): ``job_id``, ``workspace_id``,
``stage`` — short identifiers only; never corpus text or secrets.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import sys
from typing import Any

from opentelemetry import trace as otel_trace

from science_graphrag.utils.log_context import get_ingest_job_id, get_ingest_workspace_id

_CONFIGURED = False

_HTTP_LIBRARY_LOGGER_NAMES = ("httpx", "httpcore", "urllib3")
_DRAMATIQ_LOGGER_NAMES = ("dramatiq",)

# Mark our stderr handler so we still attach if another library added a handler first.
_PROJECT_HANDLER_ATTR = "_science_graphrag_project_stderr_handler"

_CORRELATION_FIELD_MAX_LEN = 128


def _truncate_correlation_value(value: str) -> str:
    """Bound correlation field length for log lines (ids only; avoid huge strings)."""
    if len(value) <= _CORRELATION_FIELD_MAX_LEN:
        return value
    cut = _CORRELATION_FIELD_MAX_LEN - 3
    return f"{value[:cut]}..."


def _parse_level(name: str, default: int) -> int:
    raw = str(name).strip()
    if not raw:
        return default
    if raw.isdigit():
        return int(raw)
    level = getattr(logging, raw.upper(), None)
    return int(level) if isinstance(level, int) else default


class _CorrelationFilter(logging.Filter):  # pylint: disable=too-few-public-methods
    """Attach job_id / workspace_id to each record for the formatter."""

    def filter(self, record: logging.LogRecord) -> bool:
        ctx_job = get_ingest_job_id()
        ctx_ws = get_ingest_workspace_id()
        if ctx_job:
            record.job_id = _truncate_correlation_value(str(ctx_job).strip())
        else:
            extra_job = getattr(record, "job_id", None)
            if extra_job not in (None, ""):
                record.job_id = _truncate_correlation_value(str(extra_job).strip())
            else:
                record.job_id = "-"
        if ctx_ws:
            record.workspace_id = _truncate_correlation_value(str(ctx_ws).strip())
        else:
            extra_ws = getattr(record, "workspace_id", None)
            if extra_ws not in (None, ""):
                record.workspace_id = _truncate_correlation_value(str(extra_ws).strip())
            else:
                record.workspace_id = "-"
        return True


_CORRELATION_FILTER = _CorrelationFilter()


class _JsonLogFormatter(logging.Formatter):  # pylint: disable=too-few-public-methods
    """One JSON object per line; run after ``_CorrelationFilter`` on the handler."""

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.datetime.fromtimestamp(record.created, tz=datetime.timezone.utc).isoformat()
        payload: dict[str, Any] = {
            "ts": ts,
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "job_id": getattr(record, "job_id", "-"),
            "workspace_id": getattr(record, "workspace_id", "-"),
        }
        stage = getattr(record, "stage", None)
        if stage is not None and str(stage).strip():
            payload["stage"] = str(stage).strip()
        trace_hex = _current_otel_trace_id_hex()
        if trace_hex:
            payload["trace_id"] = trace_hex
        if record.exc_info and record.exc_info[0] is not None:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def _current_otel_trace_id_hex() -> str | None:
    """Hex OTel trace id when a valid span context is active (for log/trace correlation)."""
    try:
        ctx = otel_trace.get_current_span().get_span_context()
    except (AttributeError, ValueError, TypeError):
        return None
    if not getattr(ctx, "is_valid", False):
        return None
    tid = getattr(ctx, "trace_id", 0) or 0
    if tid == 0:
        return None
    return format(int(tid), "032x")


def _project_stderr_handler_attached(root_sg: logging.Logger) -> bool:
    return any(getattr(h, _PROJECT_HANDLER_ATTR, False) for h in root_sg.handlers)


def _apply_http_library_log_levels() -> None:
    raw = os.getenv("SCIENCE_GRAPHRAG_HTTP_LOG_LEVEL", "WARNING")
    level = _parse_level(str(raw).strip(), logging.WARNING)
    for name in _HTTP_LIBRARY_LOGGER_NAMES:
        logging.getLogger(name).setLevel(level)


def _apply_dramatiq_log_levels() -> None:
    raw = os.getenv("SCIENCE_GRAPHRAG_DRAMATIQ_LOG_LEVEL", "WARNING")
    level = _parse_level(str(raw).strip(), logging.WARNING)
    for name in _DRAMATIQ_LOGGER_NAMES:
        logging.getLogger(name).setLevel(level)


def describe_http_log_level_env() -> str:
    """Human-readable ``SCIENCE_GRAPHRAG_HTTP_LOG_LEVEL`` for config-check / operators."""
    raw = os.getenv("SCIENCE_GRAPHRAG_HTTP_LOG_LEVEL", "WARNING")
    level = _parse_level(str(raw).strip(), logging.WARNING)
    return f"{raw!r} -> {logging.getLevelName(level)}"


def describe_dramatiq_log_level_env() -> str:
    """Human-readable ``SCIENCE_GRAPHRAG_DRAMATIQ_LOG_LEVEL`` for config-check / operators."""
    raw = os.getenv("SCIENCE_GRAPHRAG_DRAMATIQ_LOG_LEVEL", "WARNING")
    level = _parse_level(str(raw).strip(), logging.WARNING)
    return f"{raw!r} -> {logging.getLevelName(level)}"


def describe_log_format_env() -> str:
    """Active stderr log format for ``science_graphrag`` (text vs json)."""
    raw = os.getenv("SCIENCE_GRAPHRAG_LOG_FORMAT", "text").strip().lower()
    if raw in {"json", "application/json"}:
        return "json"
    return "text"


def describe_ingest_log_level_env() -> str:
    """Optional ``SCIENCE_GRAPHRAG_LOG_LEVEL_INGEST`` for ``science_graphrag.ingestion`` subtree."""
    raw = os.getenv("SCIENCE_GRAPHRAG_LOG_LEVEL_INGEST", "").strip()
    if not raw:
        return "(unset; inherits root science_graphrag level)"
    level = _parse_level(raw, logging.INFO)
    return f"{raw!r} -> {logging.getLevelName(level)}"


def reset_project_logging_for_tests() -> None:
    """Detach project stderr handler (tests only)."""
    global _CONFIGURED  # pylint: disable=global-statement
    root_sg = logging.getLogger("science_graphrag")
    for h in list(root_sg.handlers):
        if getattr(h, _PROJECT_HANDLER_ATTR, False):
            root_sg.removeHandler(h)
    logging.getLogger("science_graphrag.ingestion").setLevel(logging.NOTSET)
    _CONFIGURED = False


def _build_stderr_formatter() -> logging.Formatter:
    if describe_log_format_env() == "json":
        return _JsonLogFormatter()
    return logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s "
        "[job_id=%(job_id)s workspace_id=%(workspace_id)s]: %(message)s"
    )


def configure_logging() -> None:
    """Idempotent handler + formatter for ``science_graphrag``; tune HTTP library loggers."""
    global _CONFIGURED  # pylint: disable=global-statement
    if _CONFIGURED:
        return
    level_name = os.getenv("SCIENCE_GRAPHRAG_LOG_LEVEL", "INFO").strip()
    level = _parse_level(level_name, logging.INFO)
    root_sg = logging.getLogger("science_graphrag")
    root_sg.setLevel(level)
    ingest_override = os.getenv("SCIENCE_GRAPHRAG_LOG_LEVEL_INGEST", "").strip()
    if ingest_override:
        ingest_level = _parse_level(ingest_override, level)
        logging.getLogger("science_graphrag.ingestion").setLevel(ingest_level)
    if not _project_stderr_handler_attached(root_sg):
        fmt = _build_stderr_formatter()
        handler = logging.StreamHandler(sys.stderr)
        handler.addFilter(_CORRELATION_FILTER)
        handler.setFormatter(fmt)
        setattr(handler, _PROJECT_HANDLER_ATTR, True)
        root_sg.addHandler(handler)
    _apply_http_library_log_levels()
    _apply_dramatiq_log_levels()
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Logger under ``science_graphrag.<name>``."""
    configure_logging()
    return logging.getLogger(f"science_graphrag.{name}")
