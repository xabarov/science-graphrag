"""Markdown extraction from ingest source files (PDF via VL/pypdf; text as-is)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from science_graphrag.config import Settings
from science_graphrag.ingestion.cache_policy import read_cached_markdown
from science_graphrag.ingestion.llm.raw_openai_transport import ChatCompletionsNonJsonResponseError
from science_graphrag.ingestion.pdf import extract_text_from_pdf
from science_graphrag.ingestion.vl_pdf import VLAPIError, VLPDFProcessor
from science_graphrag.observability.phoenix_tracer import chain_span
from science_graphrag.utils.project_logging import get_logger

logger = get_logger("ingestion.markdown_extraction")


def markdown_from_path(
    path: Path,
    settings: Settings,
    *,
    document_id: str | None = None,
    on_vl_page_progress: Any | None = None,
    on_vl_batches_ready: Any | None = None,
    bypass_markdown_cache: bool = False,
) -> tuple[str, str, dict]:
    """Return (markdown, extraction_mode, vl_stats) where vl_stats may be empty dict."""

    suf = path.suffix.lower()
    if suf != ".pdf":
        return path.read_text(encoding="utf-8", errors="replace"), "plain-text", {}

    reuse_cache = bool(settings.reuse_cached_markdown) and not bypass_markdown_cache

    if reuse_cache:
        cached = read_cached_markdown(
            settings,
            path,
            document_id=document_id,
            bypass_cache=bypass_markdown_cache,
        )
        if cached is not None:
            return cached[0], cached[1], {}

    with chain_span(
        "ingest.parse_pdf.markdown",
        {"use_vl": settings.use_vl_for_pdf, "path": path.name},
    ):
        if settings.use_vl_for_pdf:
            try:
                processor = VLPDFProcessor(settings)
                markdown = processor.pdf_to_markdown(
                    path,
                    on_page_progress=on_vl_page_progress,
                    on_batches_ready=on_vl_batches_ready,
                )
                vl_stats = {
                    "vl_pages_total": processor.last_pages_total,
                    "vl_pages_processed": processor.last_pages_processed,
                    "vl_batch_count": processor.last_batch_count,
                }
                return markdown, "vl", vl_stats
            except (
                VLAPIError,
                ValueError,
                ChatCompletionsNonJsonResponseError,
                httpx.HTTPError,
                OSError,
                RuntimeError,
                TypeError,
                KeyError,
                json.JSONDecodeError,
            ) as exc:
                fb_type = getattr(exc, "__class__", type(exc)).__name__
                msg = str(exc)
                logger.warning(
                    "VL PDF failed for %s: %s; falling back to pypdf (%s)",
                    path.name,
                    msg,
                    fb_type,
                )
                fb = {
                    "ingest_transport": "vl_pdf",
                    "markdown_fallback_from": "vl",
                    "markdown_fallback_to": "pypdf-fallback",
                    "markdown_fallback_error_type": fb_type,
                    "markdown_fallback_error_message": msg[:2000],
                }
                md = extract_text_from_pdf(path)
                if on_vl_page_progress is not None:
                    try:
                        on_vl_page_progress(1, 1)
                    except Exception:  # pylint: disable=broad-exception-caught  # optional UI callback
                        pass
                return md, "pypdf-fallback", fb

        md = extract_text_from_pdf(path)
        if on_vl_page_progress is not None:
            try:
                on_vl_page_progress(1, 1)
            except Exception:  # pylint: disable=broad-exception-caught  # optional UI callback
                pass
        return md, "pypdf-fallback", {}
