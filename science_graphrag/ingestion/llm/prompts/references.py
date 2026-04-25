"""Prompt text for references extraction."""

from __future__ import annotations

INSTRUCTION_BASE = (
    "Extract bibliography entries from the references section. For each entry include "
    "raw_reference (full bibliography line or merged wrapped lines), doi if present, "
    "and arxiv_id (YYMM.NNNNN) if the line mentions arXiv or abs/."
)

INSTRUCTION_WITH_TITLES_SUFFIX = " Also include title if obvious and publication year if present."

SYSTEM_SUFFIX = (
    " References list only; preserve one bibliography item per entry and capture "
    "DOI/arXiv identifiers faithfully."
)
