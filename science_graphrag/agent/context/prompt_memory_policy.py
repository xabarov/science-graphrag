"""Precedence / fallback policy for CH4 prompt memory (Epic A2).

Resolves ``last_turn_digest`` > ``thread_insight`` (when fresh) > ``session_summary``
for ``format_user_with_memory`` and emits coarse telemetry for ``run_metadata``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from science_graphrag.config import Settings


def _rolling_digest_lines(*, window: list[dict[str, Any]]) -> str:
    """Format Q/A lines like session_backend rolling summary (stable, bounded)."""
    parts: list[str] = []
    for d in window:
        u = str(d.get("user_intent") or "")[:200]
        a = str(d.get("answer_excerpt") or "")[:300]
        if u or a:
            parts.append(f"Q: {u}\nA: {a}")
    return "\n---\n".join(parts)


def _format_last_digest_block(last: dict[str, Any]) -> str:
    ui = str(last.get("user_intent") or "").strip()
    ae = str(last.get("answer_excerpt") or "").strip()
    ac = str(last.get("answer_class") or "").strip()
    tools = last.get("tools_used") or []
    tlist = ", ".join(str(x) for x in tools if str(x).strip()) if isinstance(tools, list) else ""
    lines = [f"user_intent: {ui}", f"answer_excerpt: {ae}", f"answer_class: {ac}"]
    if tlist:
        lines.append(f"tools_used: {tlist}")
    return "\n".join(lines)


def _norm_alnum_key(text: str, *, max_len: int = 80) -> str:
    s = re.sub(r"[^a-z0-9]+", "", str(text or "").lower())[:max_len]
    return s


def _last_ptl_retry_count(session_meta: dict[str, Any]) -> int:
    audits = session_meta.get("l4_llm_compacts") or []
    if not isinstance(audits, list) or not audits:
        return 0
    last = audits[-1]
    if not isinstance(last, dict):
        return 0
    inner = last.get("llm_compact") if isinstance(last.get("llm_compact"), dict) else last
    if not isinstance(inner, dict):
        return 0
    try:
        raw_pc = inner.get("ptl_retry_count_per_compaction")
        if raw_pc is not None and str(raw_pc).strip() != "":
            return max(0, int(raw_pc))
        return max(0, int(inner.get("ptl_retry_count") or 0))
    except (TypeError, ValueError):
        return 0


def _decide_insight_injection(
    *,
    digests: list[dict[str, Any]],
    meta_dict: dict[str, Any],
    tip_dict: dict[str, Any] | None,
    current_body: str,
    turn_counter: int,
    settings: Settings,
) -> tuple[str | None, bool, str | None, bool]:
    """Return ``(fallback_reason, inject_insight, status, conflict_resolved)``."""
    circuit = (
        meta_dict.get("insight_circuit")
        if isinstance(meta_dict.get("insight_circuit"), dict)
        else {}
    )
    open_until = int(circuit.get("open_until_turn") or 0)
    circuit_open = bool(open_until and turn_counter < open_until)

    if not settings.agent_thread_insights_enabled:
        return None, False, None, False
    if circuit_open:
        return "insight_circuit_open", False, None, False
    if not tip_dict or not current_body:
        return "no_thread_insight_snapshot", False, None, False

    built_turn = _built_turn_from_insight(tip_dict)
    if built_turn is None or built_turn < turn_counter:
        return "insight_stale_lag", False, None, False

    status: str | None = "fresh"
    conflict_resolved = False
    last_digest_text = _format_last_digest_block(digests[-1]) if digests else ""
    if last_digest_text:
        ui = str((digests[-1] if digests else {}).get("user_intent") or "")
        needle = _norm_alnum_key(ui, max_len=96)
        if len(needle) >= 8:
            hay = _norm_alnum_key(current_body, max_len=12000)
            if needle not in hay:
                status = "conflicted"
                conflict_resolved = True
    return None, True, status, conflict_resolved


def _session_memory_after_policy(
    *,
    raw_summary: str,
    digests: list[dict[str, Any]],
    inject_insight: bool,
    last_digest_text: str | None,
) -> str:
    """Trim rolling summary when last digest is already shown with a fresh insight."""
    session_text = raw_summary
    if last_digest_text and inject_insight and len(digests) > 1:
        prior = digests[:-1]
        session_text = _rolling_digest_lines(window=prior[-3:])
    elif last_digest_text and inject_insight:
        session_text = ""
    return session_text


def _built_turn_from_insight(tip: dict[str, Any]) -> int | None:
    aud = tip.get("audit")
    if not isinstance(aud, dict):
        return None
    raw = aud.get("built_at_turn_counter")
    if raw is None or raw == "":
        raw = aud.get("turn_counter")
    try:
        v = int(raw or 0)
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None


@dataclass(frozen=True, slots=True)
class PromptMemoryResolution:
    """Resolved memory layers for one agent turn (before current digest is appended)."""

    last_turn_digest_text: str | None
    thread_insight_text: str | None
    thread_insight_status: str | None  # "fresh" | "conflicted" when injected
    session_memory_text: str
    insight_fallback_reason: str | None
    insight_conflict_resolved: bool
    ptl_retry_count: int

    def run_metadata_fragment(self) -> dict[str, Any]:
        """Top-level keys merged into agent ``run_metadata`` (sync + SSE)."""
        frag: dict[str, Any] = {
            "insight_conflict_resolved": bool(self.insight_conflict_resolved),
            "insight_fallback_reason": self.insight_fallback_reason,
            "ptl_retry_count": int(self.ptl_retry_count),
            "ptl_retry_count_per_compaction": int(self.ptl_retry_count),
        }
        if self.thread_insight_text and str(self.thread_insight_text).strip():
            frag["thread_insight_prompt_injected"] = True
            frag["thread_insight_prompt_status"] = self.thread_insight_status or "fresh"
        else:
            frag["thread_insight_prompt_injected"] = False
            frag["thread_insight_prompt_status"] = "omitted"
        frag["last_turn_digest_injected"] = bool(
            self.last_turn_digest_text and str(self.last_turn_digest_text).strip()
        )
        return frag


def resolve_prompt_memory_policy(
    *,
    session_ent: dict[str, Any],
    settings: Settings,
) -> PromptMemoryResolution:
    """Resolve memory layers from a defensive session copy (``get_session_for_thread``)."""
    digests = [d for d in (session_ent.get("digests") or []) if isinstance(d, dict)]
    raw_summary = str(session_ent.get("session_summary") or "").strip()
    meta = session_ent.get("session_meta") or {}
    meta_dict = dict(meta) if isinstance(meta, dict) else {}
    turn_counter = int(meta_dict.get("turn_counter") or 0)

    last_digest_text: str | None = None
    if digests:
        last_digest_text = _format_last_digest_block(digests[-1])

    tip = meta_dict.get("thread_insight")
    tip_dict = dict(tip) if isinstance(tip, dict) else None
    current_body = str(tip_dict.get("current") or "").strip() if tip_dict else ""

    fallback_reason, inject_insight, status, conflict_resolved = _decide_insight_injection(
        digests=digests,
        meta_dict=meta_dict,
        tip_dict=tip_dict,
        current_body=current_body,
        turn_counter=turn_counter,
        settings=settings,
    )

    insight_text: str | None = current_body if inject_insight else None
    insight_status = status if inject_insight else None

    session_text = _session_memory_after_policy(
        raw_summary=raw_summary,
        digests=digests,
        inject_insight=inject_insight,
        last_digest_text=last_digest_text,
    )

    return PromptMemoryResolution(
        last_turn_digest_text=last_digest_text,
        thread_insight_text=insight_text,
        thread_insight_status=insight_status,
        session_memory_text=session_text,
        insight_fallback_reason=fallback_reason,
        insight_conflict_resolved=conflict_resolved,
        ptl_retry_count=_last_ptl_retry_count(meta_dict),
    )
