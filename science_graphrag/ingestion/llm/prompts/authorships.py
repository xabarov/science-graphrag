"""Prompt text for authorship extraction."""

from __future__ import annotations

USER_PROMPT_TEMPLATE = (
    "From the following scholarly markdown, extract authors in manuscript order. "
    "Map superscripts / markers (* † ‡) on names to the affiliation line(s) below authors. "
    "Each affiliation string should match the PDF (e.g. 'University of Washington'). "
    "Provide corresponding flag and email only if explicitly indicated.\n\n---\n{meta_text}"
)

SYSTEM_SUFFIX = " Authors only; preserve order; recover affiliations from markers."
