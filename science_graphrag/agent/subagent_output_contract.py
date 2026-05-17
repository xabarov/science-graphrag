"""Prompt discipline helpers for writer / verification-style outputs (Train T2 §10.4).

No subagent runtime here — only reusable directives, output-shape text, and handoff guards.
Phase 4 adds ``ManagedReportProtocol`` parsing and typed merge field extraction.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Final

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

WEB_FETCH_FAILURE_SYNTHESIS_DIRECTIVE: Final[str] = (
    "When web_search returned external_web metadata but one or more web_fetch calls failed, do not "
    "turn the answer into a blanket refusal. Use the web_search titles/DOIs/URLs as limited web "
    "sources, clearly say that full-text fetch failed for those URLs, avoid inventing quotes or "
    "full-text claims, and cite the available URLs."
)

NEGATIVE_CLAIM_GUARD_DIRECTIVE: Final[str] = (
    "Negative-claim guard: do not state that official announcements, releases, or vendor pages "
    "'were not found', 'are not recorded', or 'do not exist' unless specialist_results include "
    "an official_web_lookup or web_fetch from an official-tier source (vendor docs, GitHub org, "
    "primary product site) that explicitly supports absence. "
    "If only scholarly/metadata sources were retrieved, say evidence is limited to those sources "
    "and that official vendor pages were not successfully fetched in this run."
)

EVIDENCE_TRUST_DIRECTIVE: Final[str] = (
    "Evidence honesty: structured citations may include provenance_kind and evidence_mode. "
    "Do not claim you read the full PDF or full article text unless evidence_mode is full_text or "
    "provenance is workspace_full_text or extracted_pdf_text from actual extraction. "
    "When evidence_mode is metadata_only, abstract, web_summary, or oa_link, state that limitation "
    "explicitly and avoid passage-level claims you cannot ground. Prefer stronger evidence over "
    "weaker metadata when they disagree."
)

METADATA_QUALITY_GUARD_DIRECTIVE: Final[str] = (
    "Source-quality guard: when citations are mostly metadata_only (Crossref/S2/OpenAlex) "
    "or failed/boilerplate web summaries, label conclusions as tentative and avoid wording "
    "that implies full-text confirmation."
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
    parts = [
        "## WriterEvidenceDirectives",
        "Must: synthesize concrete claims from specialist_results; call final_answer with limitations when thin.",
        "Must-not: delegate with vague meta ('based on your findings'); generic refusal when partial evidence exists.",
        SYNTHESIZE_NOT_DELEGATE_DIRECTIVE,
        WEB_FETCH_FAILURE_SYNTHESIS_DIRECTIVE,
        NEGATIVE_CLAIM_GUARD_DIRECTIVE,
        EVIDENCE_TRUST_DIRECTIVE,
        METADATA_QUALITY_GUARD_DIRECTIVE,
    ]
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


def read_only_subagent_answer_matches_contract(answer: str) -> bool:
    """§10.4 strict layout without VERDICT (corpus-explore and similar read-only roles)."""
    s = str(answer or "")
    if not s.strip():
        return False
    if re.search(r"(?m)^\s*VERDICT\s*:", s, re.IGNORECASE):
        return False
    return bool(
        re.search(r"(?m)^\s*Scope\s*:", s)
        and re.search(r"(?m)^\s*Result\s*:", s)
        and re.search(r"(?m)^\s*Key sources\s*:", s)
    )


_RESEARCH_PLAN_SECTIONS = (
    r"(?is)Corpus\s+sub-queries\s*:",
    r"(?is)Graph\s+sub-queries\s*:",
    r"(?is)Writer\s+spec\s*:",
)

# Phase 4 — smolagents managed-agent report sections (prompt + parser contract).
MANAGED_REPORT_PROTOCOL_HEADER: Final[str] = "## ManagedReportProtocol"
MANAGED_REPORT_SECTION_SHORT: Final[str] = "Task outcome (short)"
MANAGED_REPORT_SECTION_DETAILED: Final[str] = "Task outcome (detailed)"
MANAGED_REPORT_SECTION_LIMITATIONS: Final[str] = "Open limitations / next checks"

MANAGED_REPORT_PROTOCOL_BLOCK: Final[str] = f"""{MANAGED_REPORT_PROTOCOL_HEADER}
After your existing Scope/Result/Key sources lines (when applicable), also include:
{MANAGED_REPORT_SECTION_SHORT}: <one line>
{MANAGED_REPORT_SECTION_DETAILED}: <2-6 sentences>
{MANAGED_REPORT_SECTION_LIMITATIONS}: <bullets; prefix follow-ups with "Next check:">
"""

_RE_MANAGED_SHORT = re.compile(
    rf"(?is)^\s*{re.escape(MANAGED_REPORT_SECTION_SHORT)}\s*:\s*(.+?)"
    rf"(?=^\s*{re.escape(MANAGED_REPORT_SECTION_DETAILED)}\s*:|"
    rf"^\s*{re.escape(MANAGED_REPORT_SECTION_LIMITATIONS)}\s*:|\Z)",
    re.MULTILINE,
)
_RE_MANAGED_DETAILED = re.compile(
    rf"(?is)^\s*{re.escape(MANAGED_REPORT_SECTION_DETAILED)}\s*:\s*(.+?)"
    rf"(?=^\s*{re.escape(MANAGED_REPORT_SECTION_LIMITATIONS)}\s*:|\Z)",
    re.MULTILINE,
)
_RE_MANAGED_LIMITATIONS = re.compile(
    rf"(?is)^\s*{re.escape(MANAGED_REPORT_SECTION_LIMITATIONS)}\s*:\s*(.+?)\Z",
    re.MULTILINE,
)
_RE_SCOPE = re.compile(r"(?im)^\s*Scope\s*:\s*(.+)$")
_RE_RESULT = re.compile(r"(?is)^\s*Result\s*:\s*(.+?)(?=^\s*Key sources\s*:|\Z)", re.MULTILINE)

_NEXT_CHECK_PREFIXES = (
    "next check:",
    "next:",
    "follow-up:",
    "follow up:",
    "retry:",
)


def _bullet_lines(block: str) -> list[str]:
    out: list[str] = []
    for raw in str(block or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        line = re.sub(r"^[-*•]\s*", "", line).strip()
        line = re.sub(r"^\d+[\.\)]\s*", "", line).strip()
        if line:
            out.append(line)
    return out[:32]


def _split_limitations_and_next_checks(block: str) -> tuple[list[str], list[str]]:
    limitations: list[str] = []
    next_checks: list[str] = []
    for line in _bullet_lines(block):
        low = line.lower()
        if any(low.startswith(p) for p in _NEXT_CHECK_PREFIXES):
            next_checks.append(line)
        else:
            limitations.append(line)
    return limitations, next_checks


def parse_managed_report_from_text(text: str) -> dict[str, Any]:
    """Extract typed managed-report fields from subagent plain-text output."""
    s = str(text or "")
    outcome_short = ""
    outcome_detailed = ""
    limitations: list[str] = []
    next_checks: list[str] = []
    sections_present = False

    m_short = _RE_MANAGED_SHORT.search(s)
    if m_short:
        sections_present = True
        outcome_short = str(m_short.group(1) or "").strip()[:500]
    m_det = _RE_MANAGED_DETAILED.search(s)
    if m_det:
        sections_present = True
        outcome_detailed = str(m_det.group(1) or "").strip()[:4000]
    m_lim = _RE_MANAGED_LIMITATIONS.search(s)
    if m_lim:
        sections_present = True
        lims, nxt = _split_limitations_and_next_checks(str(m_lim.group(1) or ""))
        limitations.extend(lims)
        next_checks.extend(nxt)

    if not sections_present:
        scope_m = _RE_SCOPE.search(s)
        result_m = _RE_RESULT.search(s)
        if scope_m or result_m:
            scope_txt = str(scope_m.group(1) or "").strip() if scope_m else ""
            result_txt = str(result_m.group(1) or "").strip() if result_m else ""
            outcome_short = scope_txt or result_txt[:200]
            outcome_detailed = result_txt[:4000]
            lims, nxt = _split_limitations_and_next_checks(result_txt)
            limitations.extend(lims)
            next_checks.extend(nxt)

    return {
        "outcome_summary": outcome_short,
        "outcome_detailed": outcome_detailed,
        "limitations": limitations,
        "next_checks": next_checks,
        "report_sections_present": sections_present,
    }


def managed_report_answer_matches_contract(answer: str) -> bool:
    """True when explicit ManagedReportProtocol sections are present."""
    parsed = parse_managed_report_from_text(answer)
    if not parsed.get("report_sections_present"):
        return False
    return bool(str(parsed.get("outcome_summary") or "").strip())


def merge_limitation_signals(merge: dict[str, Any] | None) -> tuple[list[str], list[str]]:
    """Return typed ``limitations`` and ``next_checks`` lists from a v3 merge block."""
    if not isinstance(merge, dict):
        return [], []
    raw_lims = merge.get("limitations")
    raw_nxt = merge.get("next_checks")
    lims_list = raw_lims if isinstance(raw_lims, list) else []
    nxt_list = raw_nxt if isinstance(raw_nxt, list) else []
    out_lims = [str(x).strip() for x in lims_list if str(x).strip()]
    out_nxt = [str(x).strip() for x in nxt_list if str(x).strip()]
    return out_lims[:32], out_nxt[:32]


def format_salvage_limitation_lines(
    *,
    language: str,
    limitations: list[str],
    next_checks: list[str],
    outcome_summary: str = "",
    writer_directive: str = "",
) -> list[str]:
    """Build human-facing salvage lines from typed merge fields (Phase 4/5 contract)."""
    lines: list[str] = []
    summary = str(outcome_summary or "").strip()
    directive = str(writer_directive or "").strip()
    lims = [str(x).strip() for x in limitations if str(x).strip()][:6]
    nxt = [str(x).strip() for x in next_checks if str(x).strip()][:6]
    if language == "ru":
        if summary:
            lines.append(f"- краткий итог субагентов: {summary[:300]}")
        if lims:
            lines.append("- ограничения: " + "; ".join(lims))
        if nxt:
            lines.append("- следующие шаги: " + "; ".join(nxt))
        if directive and not lims and not nxt:
            lines.append(f"- замечания merge: {directive[:600]}")
        return lines
    if summary:
        lines.append(f"- subagent outcome (short): {summary[:300]}")
    if lims:
        lines.append("- limitations: " + "; ".join(lims))
    if nxt:
        lines.append("- next checks: " + "; ".join(nxt))
    if directive and not lims and not nxt:
        lines.append(f"- merge notes: {directive[:600]}")
    return lines


def research_plan_subagent_answer_matches_contract(answer: str) -> bool:
    """Executable research-plan shape: Scope/Result/Key sources + three subsection headers."""
    s = str(answer or "")
    if not read_only_subagent_answer_matches_contract(s):
        return False
    return all(re.search(p, s) for p in _RESEARCH_PLAN_SECTIONS)
