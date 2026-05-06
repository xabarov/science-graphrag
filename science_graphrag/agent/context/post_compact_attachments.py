"""Post-compact paper source capsule (Train T2 §10.5.2).

Persists a bounded list of recent paper refs after ``context_compacted`` and re-injects them on the
next user prompt via ``format_user_with_memory``.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from langchain_core.messages import ToolMessage

from science_graphrag.agent.context.session_backend import get_session_memory_backend
from science_graphrag.agent.tool_call_normalization import normalize_tool_call_name

if TYPE_CHECKING:
    from science_graphrag.config import Settings


def extract_paper_source_items_from_messages(
    messages: list[Any],
    *,
    max_items: int,
) -> list[dict[str, Any]]:
    """Collect recent ``idea_search`` / ``paper_quote_search`` work refs from tool JSON."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    cap = max(1, int(max_items))
    for msg in reversed(list(messages or [])):
        if len(out) >= cap:
            break
        if not isinstance(msg, ToolMessage):
            continue
        name = normalize_tool_call_name(str(getattr(msg, "name", "") or ""))
        raw = str(msg.content or "").strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        if name == "idea_search":
            items = payload.get("items")
            if not isinstance(items, list):
                continue
            for it in items:
                if len(out) >= cap:
                    break
                if not isinstance(it, dict):
                    continue
                wid = str(it.get("work_id") or it.get("id") or "").strip()
                sn = str(it.get("snippet") or "")[:400]
                if not wid:
                    continue
                if wid in seen:
                    continue
                seen.add(wid)
                out.append({"work_id": wid, "snippet": sn, "source": "idea_search"})
        elif name == "paper_quote_search":
            qcs = payload.get("quote_candidates")
            if not isinstance(qcs, list):
                continue
            for qc in qcs:
                if len(out) >= cap:
                    break
                if not isinstance(qc, dict):
                    continue
                wid = str(qc.get("work_id") or "").strip()
                sn = str(qc.get("quote_text") or "")[:400]
                key = wid or sn[:48]
                if not key or key in seen:
                    continue
                seen.add(key)
                out.append({"work_id": wid, "snippet": sn, "source": "paper_quote_search"})
    return out


def persist_post_compact_paper_sources(
    thread_id: str,
    messages: list[Any] | None,
    *,
    settings: "Settings",
) -> dict[str, Any]:
    """Store capsule under ``session_meta.post_compact_paper_sources``."""
    audit: dict[str, Any] = {"post_compact_paper_sources_saved": 0}
    tid = (thread_id or "").strip()
    if not tid:
        return audit
    if not bool(getattr(settings, "agent_post_compact_paper_sources_enabled", True)):
        return audit
    max_items = max(1, int(getattr(settings, "agent_post_compact_paper_sources_max_items", 12)))
    items = extract_paper_source_items_from_messages(list(messages or []), max_items=max_items)
    if not items:
        return audit
    capsule = {"schema_version": 1, "items": items}
    get_session_memory_backend().patch_session_meta(
        tid, patch={"post_compact_paper_sources": capsule}
    )
    audit["post_compact_paper_sources_saved"] = len(items)
    return audit


def load_paper_sources_items(session_ent: dict[str, Any]) -> list[dict[str, Any]]:
    """Read items from session copy (defensive)."""
    meta = session_ent.get("session_meta") or {}
    if not isinstance(meta, dict):
        return []
    raw = meta.get("post_compact_paper_sources")
    if not isinstance(raw, dict):
        return []
    its = raw.get("items")
    if not isinstance(its, list):
        return []
    return [x for x in its if isinstance(x, dict)]


def clear_paper_sources_capsule(thread_id: str) -> None:
    """Clear capsule after injecting into the user prompt (one-shot restore)."""
    tid = (thread_id or "").strip()
    if not tid:
        return
    get_session_memory_backend().patch_session_meta(
        tid,
        patch={"post_compact_paper_sources": {"schema_version": 1, "items": []}},
    )
