"""Session persistence for ``research_plan_write`` (session_meta.research_plan)."""

from __future__ import annotations

import time
from typing import Any

from science_graphrag.agent.context.session_backend import get_session_memory_backend
from science_graphrag.agent.context.session_store import get_session_for_thread

_ALLOWED_STATUS = frozenset({"pending", "in_progress", "completed", "cancelled"})

_RU_SEED_FIND_SOURCES = (
    "Найти наиболее релевантные источники и подтверждающие материалы " "в рабочей области."
)
_RU_SEED_SCOPE = "Уточнить цель запроса и критерии ответа."
_EN_SEED_SCOPE = "Clarify the request goal and answer criteria."


def _norm_item(raw: dict[str, Any]) -> dict[str, Any] | None:
    iid = str(raw.get("id") or "").strip()
    content = str(raw.get("content") or "").strip()
    status = str(raw.get("status") or "pending").strip().lower()
    if not iid or not content:
        return None
    if status not in _ALLOWED_STATUS:
        status = "pending"
    return {"id": iid, "content": content[:2000], "status": status}


def _load_prev_plan_index(prev: Any) -> tuple[dict[str, dict[str, Any]], list[str]]:
    by_id: dict[str, dict[str, Any]] = {}
    prev_order_ids: list[str] = []
    if not isinstance(prev, dict):
        return by_id, prev_order_ids
    raw_items = prev.get("items") or []
    if not isinstance(raw_items, list):
        return by_id, prev_order_ids
    for it in raw_items:
        if isinstance(it, dict) and str(it.get("id") or "").strip():
            pid = str(it["id"]).strip()
            prev_order_ids.append(pid)
            by_id[pid] = dict(it)
    return by_id, prev_order_ids


def _apply_incoming_plan_rows(
    by_id: dict[str, dict[str, Any]],
    items: list[dict[str, Any]],
) -> list[str]:
    incoming_order: list[str] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        norm = _norm_item(raw)
        if not norm:
            continue
        by_id[norm["id"]] = norm
        if norm["id"] not in incoming_order:
            incoming_order.append(norm["id"])
    return incoming_order


def _stable_ordered_item_ids(
    prev_order_ids: list[str],
    incoming_order: list[str],
    by_id: dict[str, dict[str, Any]],
) -> list[str]:
    ordered_ids: list[str] = []
    for iid in prev_order_ids:
        if iid in by_id and iid not in ordered_ids:
            ordered_ids.append(iid)
    for iid in incoming_order:
        if iid not in ordered_ids:
            ordered_ids.append(iid)
    for iid in by_id:
        if iid not in ordered_ids:
            ordered_ids.append(iid)
    return ordered_ids[:200]


def _resolve_plan_ui_mode(prev: Any, *, incoming_ui: str | None) -> str | None:
    prev_ui: str | None = None
    if isinstance(prev, dict):
        raw_um = prev.get("ui_mode")
        if isinstance(raw_um, str) and raw_um.strip().lower() in {"outline", "checklist"}:
            prev_ui = raw_um.strip().lower()
    if incoming_ui in {"outline", "checklist"}:
        return incoming_ui
    return prev_ui


def merge_research_plan_items(
    thread_id: str,
    items: list[dict[str, Any]],
    *,
    ui_mode: str | None = None,
) -> dict[str, Any]:
    """Merge items by ``id`` into ``session_meta.research_plan``; return new plan dict."""
    tid = (thread_id or "").strip()
    if not tid:
        plan: dict[str, Any] = {
            "schema_version": "research_plan_v1",
            "items": [],
            "updated_at": time.time(),
        }
        if isinstance(ui_mode, str) and ui_mode.strip().lower() in {"outline", "checklist"}:
            plan["ui_mode"] = ui_mode.strip().lower()
        return plan
    ent = get_session_for_thread(tid)
    meta = dict(ent.get("session_meta") or {})
    prev = meta.get("research_plan")
    by_id, prev_order_ids = _load_prev_plan_index(prev)
    incoming_order = _apply_incoming_plan_rows(by_id, items)
    ordered = [by_id[i] for i in _stable_ordered_item_ids(prev_order_ids, incoming_order, by_id)]
    plan = {
        "schema_version": "research_plan_v1",
        "items": ordered,
        "updated_at": time.time(),
    }
    incoming_ui = ui_mode.strip().lower() if isinstance(ui_mode, str) and ui_mode.strip() else None
    eff = _resolve_plan_ui_mode(prev, incoming_ui=incoming_ui)
    if eff:
        plan["ui_mode"] = eff
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
    has_ru = any(("а" <= ch.lower() <= "я") or ch.lower() == "ё" for ch in q)
    if has_ru:
        seed_items = [
            {
                "id": "01_scope",
                "content": _RU_SEED_SCOPE,
                "status": "pending",
            },
            {
                "id": "02_sources",
                "content": _RU_SEED_FIND_SOURCES,
                "status": "pending",
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
                "content": _EN_SEED_SCOPE,
                "status": "pending",
            },
            {
                "id": "02_sources",
                "content": "Find the most relevant workspace sources and evidence.",
                "status": "pending",
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
        ui_mode="outline",
    )


def reset_research_plan_for_explicit_web_followup(
    thread_id: str | None,
    *,
    question: str | None = None,
) -> dict[str, Any] | None:
    """Replace current thread plan with a concise web-research outline.

    Used when a follow-up turn explicitly shifts intent to internet research, so
    the right panel does not keep showing stale corpus-plan bullets.
    """
    tid = (thread_id or "").strip()
    if not tid:
        return None
    q = " ".join(str(question or "").strip().split())
    has_ru = any(("а" <= ch.lower() <= "я") or ch.lower() == "ё" for ch in q)
    if has_ru:
        rows = [
            {
                "id": "01_web_scope",
                "content": "Уточнить веб-вопрос и критерии релевантности.",
                "status": "pending",
            },
            {
                "id": "02_web_search",
                "content": "Найти внешние источники через web_search.",
                "status": "pending",
            },
            {
                "id": "03_web_fetch",
                "content": "Открыть 1–3 ключевые URL через web_fetch и извлечь факты.",
                "status": "pending",
            },
            {
                "id": "04_web_synthesis",
                "content": "Собрать выводы и ссылки на внешние источники.",
                "status": "pending",
            },
        ]
    else:
        rows = [
            {
                "id": "01_web_scope",
                "content": "Clarify the web question and relevance criteria.",
                "status": "pending",
            },
            {
                "id": "02_web_search",
                "content": "Find external sources via web_search.",
                "status": "pending",
            },
            {
                "id": "03_web_fetch",
                "content": "Fetch 1–3 key URLs with web_fetch and extract facts.",
                "status": "pending",
            },
            {
                "id": "04_web_synthesis",
                "content": "Synthesize findings and cite external sources.",
                "status": "pending",
            },
        ]
    plan = {
        "schema_version": "research_plan_v1",
        "items": rows[:200],
        "updated_at": time.time(),
        "ui_mode": "outline",
    }
    get_session_memory_backend().patch_session_meta(tid, patch={"research_plan": plan})
    return plan


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


def _plan_items_all_pending(items: list[Any]) -> bool:
    return all(
        str(it.get("status") or "pending").strip().lower() == "pending"
        for it in items
        if isinstance(it, dict) and str(it.get("id") or "").strip()
    )


def _research_plan_outline_prompt_lines(plan: dict[str, Any], items: list[Any]) -> bool:
    ui_m = str(plan.get("ui_mode") or "").strip().lower()
    if ui_m == "outline":
        return True
    if ui_m == "checklist":
        return False
    return _plan_items_all_pending(items)


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
    outline_prompt = _research_plan_outline_prompt_lines(plan, items)
    lines = []
    for it in items[:80]:
        if not isinstance(it, dict):
            continue
        iid = str(it.get("id") or "").strip()
        st = str(it.get("status") or "").strip()
        ct = str(it.get("content") or "").strip().replace("\n", " ")[:240]
        if iid and ct:
            if outline_prompt:
                lines.append(f"- {iid}: {ct}")
            else:
                lines.append(f"- [{st}] {iid}: {ct}")
    if not lines:
        return None
    body = "\n".join(lines)
    return f"<research_plan>\n{body}\n</research_plan>"
