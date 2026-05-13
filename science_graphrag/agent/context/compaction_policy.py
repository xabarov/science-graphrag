"""R3: explicit L4 full-history compaction eligibility + traceable skip reasons.

Centralizes the guard logic for ``maybe_llm_compact_session_after_turn`` so
``compaction_audit`` can always record *why* L4 did or did not run, without
duplicating policy across API layers.
"""

from __future__ import annotations

from typing import Any

from science_graphrag.agent.context.session_backend import get_session_memory_backend
from science_graphrag.config import Settings


def _l4_hist_tail(session_meta: dict[str, Any]) -> tuple[int, int | None]:
    audits = session_meta.get("l4_llm_compacts") or []
    if not isinstance(audits, list) or not audits:
        return 0, None
    last = audits[-1]
    if not isinstance(last, dict):
        return len(audits), None
    inner = last.get("llm_compact") if isinstance(last.get("llm_compact"), dict) else last
    if not isinstance(inner, dict):
        return len(audits), None
    chars = inner.get("summary_chars")
    try:
        sc = int(chars) if chars is not None and str(chars).strip() != "" else None
    except (TypeError, ValueError):
        sc = None
    return len(audits), sc


def evaluate_l4_full_history_compact_eligibility(
    settings: Settings,
    thread_id: str,
    *,
    digest_count: int,
    digest_cap: int,
) -> dict[str, Any]:
    """Return a JSON-serializable audit fragment for ``compaction_audit['l4_eligibility']``.

    Side-effect free (read-only session copy). ``maybe_llm_compact_session_after_turn``
    may still skip later for ``compaction_lock`` contention or LLM failure — those are
    logged separately when they occur.
    """
    tid = (thread_id or "").strip()
    out: dict[str, Any] = {
        "schema_version": "l4_eligibility_v1",
        "l4_enabled": bool(settings.agent_llm_full_history_compact_enabled),
        "digest_count": int(digest_count),
        "digest_cap": int(digest_cap),
        "thread_id_present": bool(tid),
    }
    if not settings.agent_llm_full_history_compact_enabled:
        out["eligible"] = False
        out["skip_reason"] = "disabled"
        return out
    if not tid:
        out["eligible"] = False
        out["skip_reason"] = "empty_thread_id"
        return out
    if digest_count < digest_cap:
        out["eligible"] = False
        out["skip_reason"] = "below_digest_cap"
        out["cooldown_turns"] = max(1, int(settings.agent_llm_full_history_compact_cooldown_turns))
        return out
    if not (settings.extraction_llm_api_key or "").strip():
        out["eligible"] = False
        out["skip_reason"] = "no_extraction_api_key"
        return out

    backend = get_session_memory_backend()
    ent = backend.get_session_copy(tid)
    if not ent:
        out["eligible"] = False
        out["skip_reason"] = "session_missing"
        return out

    meta = ent.get("session_meta") or {}
    meta_dict = dict(meta) if isinstance(meta, dict) else {}
    turn_counter = int(meta_dict.get("turn_counter") or 0)
    last_compact = int(meta_dict.get("last_llm_compact_turn") or 0)
    cooldown = max(1, int(settings.agent_llm_full_history_compact_cooldown_turns))
    out["turn_counter"] = turn_counter
    out["last_llm_compact_turn"] = last_compact
    out["cooldown_turns"] = cooldown
    out["turns_since_last_llm_compact"] = turn_counter - last_compact

    if turn_counter - last_compact < cooldown:
        out["eligible"] = False
        out["skip_reason"] = "cooldown_active"
        hist_len, last_summary_chars = _l4_hist_tail(meta_dict)
        out["l4_hist_len"] = hist_len
        out["l4_last_summary_chars"] = last_summary_chars
        return out

    digests = [d for d in (ent.get("digests") or []) if isinstance(d, dict)]
    if not digests:
        out["eligible"] = False
        out["skip_reason"] = "empty_digests"
        return out

    hist_len, last_summary_chars = _l4_hist_tail(meta_dict)
    out["l4_hist_len"] = hist_len
    out["l4_last_summary_chars"] = last_summary_chars
    out["eligible"] = True
    out["skip_reason"] = None
    return out


def attach_l4_eligibility_to_compaction_audit(
    compact_payload: dict[str, Any],
    *,
    settings: Settings,
    thread_id: str,
    digest_count: int,
    digest_cap: int,
    llm_compact_applied: bool | None = None,
) -> dict[str, Any]:
    """Merge ``l4_eligibility`` into ``compact_payload['audit']`` (immutable-ish).

    When preflight says ``eligible`` and ``llm_compact_applied`` is not ``None``,
    records whether ``maybe_llm_compact_session_after_turn`` actually persisted
    a summary (``True``) or returned early (lock, empty summary, LLM error — ``False``).
    """

    aud = dict(compact_payload.get("audit") or {})
    elig = evaluate_l4_full_history_compact_eligibility(
        settings,
        thread_id,
        digest_count=digest_count,
        digest_cap=digest_cap,
    )
    if llm_compact_applied is not None and elig.get("eligible"):
        elig = {**elig, "llm_compact_applied": bool(llm_compact_applied)}
    aud["l4_eligibility"] = elig
    out = dict(compact_payload)
    out["audit"] = aud
    return out
