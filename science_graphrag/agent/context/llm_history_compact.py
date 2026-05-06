"""L4: optional LLM consolidation of full turn-digest window into ``session_summary``.

Runs when digest count reaches ``agent_compaction_digest_cap`` (boundary candidate) and
cooldown elapsed — feature-flagged (default off).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from science_graphrag.agent.context.session_backend import get_session_memory_backend
from science_graphrag.agent.llm.chat import build_chat_model, effective_chat_llm_model
from science_graphrag.config import Settings

logger = logging.getLogger(__name__)

_L4_PROMPT_VERSION = "l4_llm_compact_v1"


def _slim_digests_blob(digests: list[dict[str, Any]], *, max_chars: int) -> str:
    slim: list[dict[str, Any]] = []
    for d in digests:
        if not isinstance(d, dict):
            continue
        slim.append(
            {
                "user_intent": str(d.get("user_intent") or "")[:500],
                "answer_excerpt": str(d.get("answer_excerpt") or "")[:700],
                "answer_class": str(d.get("answer_class") or ""),
                "tools_used": list(d.get("tools_used") or [])[:24],
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

    max_in = max(2000, int(settings.agent_llm_full_history_compact_max_digest_chars))
    blob = _slim_digests_blob(digests, max_chars=max_in)
    try:
        summary = _invoke_summary_llm(settings, user_blob=blob)
    except Exception as exc:  # noqa: BLE001
        logger.warning("l4_llm_compact failed: %s", exc, exc_info=True)
        return None

    if not summary.strip():
        return None

    audit = {
        "schema_version": _L4_PROMPT_VERSION,
        "digest_count": len(digests),
        "turn_counter": turn_counter,
        "model": effective_chat_llm_model(settings),
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
