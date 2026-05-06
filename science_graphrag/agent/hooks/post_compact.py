"""Post-compact hook chain: paper sources persistence + reinject observability (§10.5.2 / §10.6)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from science_graphrag.agent.context.post_compact_attachments import (
    persist_post_compact_paper_sources,
)
from science_graphrag.agent.context.session_store import get_session_for_thread
from science_graphrag.agent.hooks.contracts import HookDecision, hook_chain_event_dict

if TYPE_CHECKING:
    from science_graphrag.config import Settings


def run_post_compact_hooks(
    *,
    thread_id: str,
    messages: list[Any] | None,
    settings: "Settings",
    out_events: list[dict[str, Any]] | None = None,
) -> list[HookDecision]:
    """Run post-compact side effects; append explainable events to ``out_events`` when provided."""
    decisions: list[HookDecision] = []
    sink = out_events if out_events is not None else []

    tid = (thread_id or "").strip()
    paper_audit: dict[str, Any] = {}
    if tid:
        paper_audit = persist_post_compact_paper_sources(tid, messages, settings=settings)
    decisions.append(
        HookDecision(
            ok=True,
            hook_id="post_compact.persist_paper_sources",
            phase="post_compact",
            detail=dict(paper_audit),
        )
    )
    sink.append(
        hook_chain_event_dict(
            hook_id="post_compact.persist_paper_sources",
            phase="post_compact",
            ok=True,
            detail=dict(paper_audit),
        )
    )

    discovered_note: dict[str, Any] = {}
    plan_note: dict[str, Any] = {}
    if tid:
        ent = get_session_for_thread(tid)
        caps = ent.get("capsules") or {}
        if isinstance(caps, dict):
            dc = caps.get("discovered_tools")
            if isinstance(dc, dict):
                rt = dc.get("recent_tools")
                if isinstance(rt, list) and rt:
                    discovered_note = {
                        "discovered_tools_carryover_count": len(rt),
                        "sample_tail": [str(x) for x in rt[-8:] if str(x).strip()],
                    }
        sm = ent.get("session_meta") or {}
        if isinstance(sm, dict) and isinstance(sm.get("research_plan"), dict):
            plan_note = {"research_plan_present": True}
        elif isinstance(sm, dict) and sm.get("research_plan_v1") is not None:
            plan_note = {"research_plan_present": True, "key": "research_plan_v1"}

    decisions.append(
        HookDecision(
            ok=True,
            hook_id="post_compact.reinject_signal",
            phase="post_compact",
            detail={"discovered_tools": discovered_note, "plan": plan_note},
        )
    )
    sink.append(
        hook_chain_event_dict(
            hook_id="post_compact.reinject_signal",
            phase="post_compact",
            ok=True,
            detail={"discovered_tools": discovered_note, "plan": plan_note},
        )
    )
    return decisions
