"""Stable client/server contract tokens for explicit PDF-read turns (Ask UI + API v2)."""

from __future__ import annotations

# Machine token persisted as the user "question" for PDF-only turns; UI must not surface raw.
PDF_READ_USER_MESSAGE_TOKEN = "__sg_pdf_read_action__"

# Default excerpt budget for read_external_pdf (tool schema + API prefetch).
# Keep aligned with ReadExternalPdfArgs defaults in pdf_read_tools.
PDF_READ_DEFAULT_EXCERPT_CHARS = 6000

__all__ = ["PDF_READ_DEFAULT_EXCERPT_CHARS", "PDF_READ_USER_MESSAGE_TOKEN"]
