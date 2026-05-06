"""L4: optional LLM consolidation of full turn-digest window into ``session_summary``.

Runs when digest count reaches ``agent_compaction_digest_cap`` (boundary candidate) and
cooldown elapsed — feature-flagged (default off). Uses compaction_lock mutual exclusion
with thread_insights refresh and optional PTL-style retries by dropping oldest digests.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from science_graphrag.agent.context.message_sanitizers import sanitize_digest_dict_for_compact
from science_graphrag.agent.context.session_backend import get_session_memory_backend
from science_graphrag.agent.llm.chat import build_chat_model, effective_chat_llm_model
from science_graphrag.config import Settings

logger = logging.getLogger(__name__)

_L4_PROMPT_VERSION = "l4_llm_compact_v1"


def _is_context_limit_error(exc: BaseException) -> bool:
    """Heuristic: provider/context errors that may succeed with a smaller input."""
    s = str(exc).lower()
    needles = (
        "token",
        "context length",
        "maximum context",
        "too many tokens",
        "max_tokens",
        "context_window",
        "length limit",
        "reduce the length",
    )
    return any(n in s for n in needles)


def _slim_digests_blob(
    digests: list[dict[str, Any]],
    *,
    max_chars: int,
    settings: Settings,
) -> str:
    slim: list[dict[str, Any]] = []
    pre_ok = bool(getattr(settings, "agent_pre_compact_sanitizers_enabled", True))
    for d in digests:
        if not isinstance(d, dict):
            continue
        src = sanitize_digest_dict_for_compact(d) if pre_ok else d
        slim.append(
            {
                "user_intent": str(src.get("user_intent") or "")[:500],
                "answer_excerpt": str(src.get("answer_excerpt") or "")[:700],
                "answer_class": str(src.get("answer_class") or ""),
                "tools_used": list(src.get("tools_used") or [])[:24],
            }
        )
    raw = json.dumps(slim, ensure_ascii=False)
    if len(raw) <= max_chars:
        return raw
    return raw[: max_chars - 10] + "\n…[truncated]"


def _invoke_summary_llm(settings: Settings, *, user_blob: str) -> str:
    llm = build_chat_model(
        settings,
        temperature=0.15,
        max_tokens=min(4096, max(512, settings.agent_llm_full_history_compact_max_out_tokens)),
        timeout_seconds=float(settings.extraction_llm_timeout_seconds),
    )
    system = (
        "You consolidate multi-turn research assistant memory. Given JSON objects with "
        "user_intent, answer_excerpt, tools_used, answer_class per turn, produce ONE dense "
        "third-person memory block the assistant will see as <session_memory>. "
        "Preserve: named papers/methods/Dataset IDs/user goals/constraints/open questions. "
        "Drop boilerplate. Use short bullets and sections if helpful. "
        "Output plain text only — no JSON, no markdown fences."
    )
    human = (
        "Turn digests (JSON array of objects):\n"
        f"{user_blob}\n\n"
        f"Max output characters (approx): {settings.agent_llm_full_history_compact_max_out_tokens * 3}"
    )
    msg = llm.invoke([SystemMessage(content=system), HumanMessage(content=human)])
    text = str(getattr(msg, "content", "") or "").strip()
    text = re.sub(r"^```[a-z]*\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def maybe_llm_compact_session_after_turn(
    settings: Settings,
    thread_id: str,
    *,
    digest_count: int,
    digest_cap: int,
) -> dict[str, Any] | None:
    """If enabled and boundary satisfied, replace ``session_summary`` via LLM. Returns audit dict."""

    if not settings.agent_llm_full_history_compact_enabled:
        return None
    if not (thread_id or "").strip():
        return None
    if digest_count < digest_cap:
        return None
    if not (settings.extraction_llm_api_key or "").strip():
        logger.warning("l4_llm_compact skipped: extraction_llm_api_key unset")
        return None

    backend = get_session_memory_backend()
    ent = backend.get_session_copy(thread_id)
    meta = ent.get("session_meta") or {}
    turn_counter = int(meta.get("turn_counter") or 0)
    last_compact = int(meta.get("last_llm_compact_turn") or 0)
    cooldown = max(1, int(settings.agent_llm_full_history_compact_cooldown_turns))
    if turn_counter - last_compact < cooldown:
        return None

    digests = [d for d in (ent.get("digests") or []) if isinstance(d, dict)]
    if not digests:
        return None

    if not backend.compaction_lock_acquire(thread_id, owner="l4", turn=turn_counter):
        logger.info("l4_llm_compact skipped: compaction_lock held")
        return None

    max_in = max(2000, int(settings.agent_llm_full_history_compact_max_digest_chars))
    max_ptl = max(0, int(settings.agent_llm_full_history_compact_ptl_max_retries))
    digests_work = list(digests)
    ptl_retry_count = 0
    summary = ""
    blob = ""
    try:
        for attempt in range(max_ptl + 1):
            blob = _slim_digests_blob(digests_work, max_chars=max_in, settings=settings)
            try:
                summary = _invoke_summary_llm(settings, user_blob=blob)
                break
            except Exception as exc:  # noqa: BLE001
                if attempt >= max_ptl or not _is_context_limit_error(exc) or len(digests_work) <= 2:
                    logger.warning("l4_llm_compact failed: %s", exc, exc_info=True)
                    return None
                digests_work = digests_work[1:]
                ptl_retry_count += 1
                logger.info(
                    "l4_llm_compact PTL retry %s dropping oldest digest (remaining=%s)",
                    ptl_retry_count,
                    len(digests_work),
                )
    finally:
        backend.compaction_lock_release(thread_id, owner="l4")

    if not summary.strip():
        return None

    audit = {
        "schema_version": _L4_PROMPT_VERSION,
        "digest_count": len(digests),
        "digest_prompt_count": len(digests_work),
        "turn_counter": turn_counter,
        "model": effective_chat_llm_model(settings),
        "ptl_retry_count": ptl_retry_count,
        "digest_blob_chars": len(blob),
        "summary_chars": len(summary),
    }
    backend.apply_llm_session_compact(thread_id, new_summary=summary, audit_fragment=audit)
    return audit


def patch_compaction_audit_llm(
    compact_payload: dict[str, Any],
    *,
    llm_audit: dict[str, Any],
) -> dict[str, Any]:
    """Mutate ``compact_payload['audit']`` after successful L4 LLM compaction."""

    aud = compact_payload.get("audit")
    if not isinstance(aud, dict):
        aud = {}
    aud = dict(aud)
    aud["llm_full_history_compact"] = True
    aud["llm_compact"] = dict(llm_audit)
    out = dict(compact_payload)
    out["audit"] = aud
    return out
