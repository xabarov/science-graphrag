"""Prompt discipline helpers for writer / verification-style outputs (Train T2 §10.4).

No subagent runtime here — only reusable directives, output-shape text, and handoff guards.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from science_graphrag.config import Settings

# Kept English to match existing specialist prompts in this package.
SYNTHESIZE_NOT_DELEGATE_DIRECTIVE: Final[str] = (
    "Synthesize, don't delegate: never address a parent or another agent with vague meta like "
    "'based on your findings' or 'as the specialists reported'. State concrete claims, evidence, "
    "and gaps. If specialist_results are thin or only summaries, infer what is missing, say so "
    "briefly, and still ground the answer in what is available (or call final_answer with explicit "
    "limitations)."
)

VERIFICATION_OUTPUT_FORMAT_BLOCK: Final[str] = (
    "When producing the user-visible answer inside final_answer.answer, use this exact section "
    "layout (markdown lines, English labels):\n"
    "Scope: <one-line restatement of the task>\n"
    "Result: <main body>\n"
    "Key sources: <comma-separated work_ids or chunk ids, or none>\n"
    "VERDICT: PASS | FAIL | PARTIAL\n"
    "Do not omit any of these four lines. VERDICT must be one of PASS, FAIL, PARTIAL."
)

_HANDOFF_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bplease\s+continue\b",
        r"\bplease\s+continue\s+from\s+here\b",
        r"\bleave\s+the\s+rest\s+to\s+you\b",
        r"\bi\s+leave\s+the\s+rest\s+to\s+you\b",
        r"\bover\s+to\s+you\b",
        r"\byou\s+take\s+it\s+from\s+here\b",
    )
)


def detect_handoff_phrase(text: str) -> bool:
    """Return True if ``text`` looks like delegating continuation to another agent."""
    s = str(text or "")
    if not s.strip():
        return False
    return any(p.search(s) for p in _HANDOFF_PATTERNS)


HANDOFF_WARNING_PREFIX: Final[str] = (
    "[warning: lazy-handoff-phrasing-detected] The answer must be self-contained; "
    "do not delegate continuation to another agent or the user without substance.\n\n"
)


def maybe_prepend_handoff_warning(answer: str) -> tuple[str, bool]:
    """If handoff-like phrasing is present, prepend a visible warning once."""
    body = str(answer or "")
    if not detect_handoff_phrase(body):
        return body, False
    if body.lstrip().startswith("[warning: lazy-handoff-phrasing-detected]"):
        return body, False
    return HANDOFF_WARNING_PREFIX + body, True


def verification_format_enabled(*, settings: "Settings") -> bool:
    """Whether strict Scope/Result/Key sources/VERDICT is requested for writer normal mode."""
    return bool(getattr(settings, "agent_writer_verification_output_format_enabled", False))


def writer_system_prompt_suffix(*, settings: "Settings", writer_mode: str) -> str:
    """Extra system text for writer (synthesize + optional verification layout)."""
    parts = [SYNTHESIZE_NOT_DELEGATE_DIRECTIVE]
    if writer_mode == "normal" and verification_format_enabled(settings=settings):
        parts.append(VERIFICATION_OUTPUT_FORMAT_BLOCK)
    return "\n\n".join(parts)


def verification_answer_matches_contract(answer: str) -> bool:
    """Heuristic contract check for tests / optional lint (not enforced at runtime by default)."""
    s = str(answer or "")
    if not s.strip():
        return False
    return bool(
        re.search(r"(?m)^\s*Scope\s*:", s)
        and re.search(r"(?m)^\s*Result\s*:", s)
        and re.search(r"(?m)^\s*Key sources\s*:", s)
        and re.search(r"(?m)^\s*VERDICT\s*:\s*(PASS|FAIL|PARTIAL)\b", s, re.IGNORECASE)
    )
