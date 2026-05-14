"""Session persistence for ``research_plan_write`` (session_meta.research_plan)."""

from __future__ import annotations

import time
from typing import Any

from science_graphrag.agent.context.session_backend import get_session_memory_backend
from science_graphrag.agent.context.session_store import get_session_for_thread

_ALLOWED_STATUS = frozenset({"pending", "in_progress", "completed", "cancelled"})


def _norm_item(raw: dict[str, Any]) -> dict[str, Any] | None:
    iid = str(raw.get("id") or "").strip()
    content = str(raw.get("content") or "").strip()
    status = str(raw.get("status") or "pending").strip().lower()
    if not iid or not content:
        return None
    if status not in _ALLOWED_STATUS:
        status = "pending"
    return {"id": iid, "content": content[:2000], "status": status}


def merge_research_plan_items(thread_id: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge items by ``id`` into ``session_meta.research_plan``; return new plan dict."""
    tid = (thread_id or "").strip()
    if not tid:
        return {"schema_version": "research_plan_v1", "items": [], "updated_at": time.time()}
    ent = get_session_for_thread(tid)
    meta = dict(ent.get("session_meta") or {})
    prev = meta.get("research_plan")
    by_id: dict[str, dict[str, Any]] = {}
    if isinstance(prev, dict):
        for it in prev.get("items") or []:
            if isinstance(it, dict) and str(it.get("id") or "").strip():
                by_id[str(it["id"]).strip()] = dict(it)
    for raw in items:
        if not isinstance(raw, dict):
            continue
        norm = _norm_item(raw)
        if norm:
            by_id[norm["id"]] = norm
    ordered = sorted(by_id.values(), key=lambda x: x["id"])
    plan = {
        "schema_version": "research_plan_v1",
        "items": ordered[:200],
        "updated_at": time.time(),
    }
    get_session_memory_backend().patch_session_meta(tid, patch={"research_plan": plan})
    return plan


def seed_research_plan_if_empty(
    thread_id: str | None, *, question: str | None = None
) -> dict[str, Any] | None:
    """Create a deterministic starter plan for request-scoped UI plan mode.

    The LLM/subagent may refine it later via ``research_plan_write``; this seed
    keeps the UI panel useful even when write tools are disabled or no
    retrieval payloads are available.
    """
    tid = (thread_id or "").strip()
    if not tid:
        return None
    ent = get_session_for_thread(tid)
    meta = ent.get("session_meta") or {}
    if isinstance(meta, dict):
        prev = meta.get("research_plan")
        if isinstance(prev, dict) and isinstance(prev.get("items"), list) and prev["items"]:
            return dict(prev)
    q = " ".join(str(question or "").strip().split())[:240]
    scope = f": {q}" if q else ""
    has_ru = any(("а" <= ch.lower() <= "я") or ch.lower() == "ё" for ch in q)
    if has_ru:
        seed_items = [
            {
                "id": "01_scope",
                "content": f"Уточнить исследовательский вопрос и рамки сравнения{scope}",
                "status": "completed",
            },
            {
                "id": "02_sources",
                "content": "Найти наиболее релевантные источники и подтверждающие материалы в рабочей области.",
                "status": "in_progress",
            },
            {
                "id": "03_synthesis",
                "content": "Сформировать выводы и итоговый ответ со ссылками на источники.",
                "status": "pending",
            },
        ]
    else:
        seed_items = [
            {
                "id": "01_scope",
                "content": f"Clarify the research question and comparison scope{scope}",
                "status": "completed",
            },
            {
                "id": "02_sources",
                "content": "Find the most relevant workspace sources and evidence.",
                "status": "in_progress",
            },
            {
                "id": "03_synthesis",
                "content": "Synthesize the answer with conclusions and citations.",
                "status": "pending",
            },
        ]
    return merge_research_plan_items(
        tid,
        seed_items,
    )


def get_research_plan_snapshot_for_thread(thread_id: str | None) -> dict[str, Any] | None:
    """Return persisted research plan dict when it has at least one item (for run_metadata / UI)."""
    tid = (thread_id or "").strip()
    if not tid:
        return None
    ent = get_session_for_thread(tid)
    meta = ent.get("session_meta") or {}
    if not isinstance(meta, dict):
        return None
    plan = meta.get("research_plan")
    if not isinstance(plan, dict):
        return None
    items = plan.get("items")
    if not isinstance(items, list) or not items:
        return None
    return dict(plan)


def research_plan_prompt_block(thread_id: str | None) -> str | None:
    """Return XML block for prompt reinjection (re-attach after compaction)."""
    tid = (thread_id or "").strip()
    if not tid:
        return None
    ent = get_session_for_thread(tid)
    meta = ent.get("session_meta") or {}
    if not isinstance(meta, dict):
        return None
    plan = meta.get("research_plan")
    if not isinstance(plan, dict):
        return None
    items = plan.get("items") or []
    if not isinstance(items, list) or not items:
        return None
    lines = []
    for it in items[:80]:
        if not isinstance(it, dict):
            continue
        iid = str(it.get("id") or "").strip()
        st = str(it.get("status") or "").strip()
        ct = str(it.get("content") or "").strip().replace("\n", " ")[:240]
        if iid and ct:
            lines.append(f"- [{st}] {iid}: {ct}")
    if not lines:
        return None
    body = "\n".join(lines)
    return f"<research_plan>\n{body}\n</research_plan>"
