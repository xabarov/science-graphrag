"""Post-compact hook chain (Train T3 §10.6)."""

from __future__ import annotations

import json

from langchain_core.messages import ToolMessage

from science_graphrag.agent.context.session_store import (
    clear_session_store_for_tests,
    get_session_for_thread,
    update_session_after_turn,
)
from science_graphrag.agent.hooks import run_post_compact_hooks
from science_graphrag.api.agent_v2_modules.payloads import merge_hook_chain_events_into_run_metadata
from science_graphrag.config import Settings


def test_run_post_compact_hooks_emits_hook_chain_events() -> None:
    try:
        tid = "t_hooks_post_compact"
        update_session_after_turn(
            tid,
            turn_digest={
                "user_intent": "q",
                "answer_excerpt": "a",
                "answer_class": "x",
                "tools_used": ["idea_search"],
            },
        )
        st = Settings.model_construct(
            agent_post_compact_paper_sources_enabled=True,
            agent_post_compact_paper_sources_max_items=12,
        )
        msgs = [
            ToolMessage(
                content=json.dumps({"items": [{"work_id": "w1", "snippet": "s1"}]}),
                tool_call_id="tc1",
                name="idea_search",
            )
        ]
        events: list[dict] = []
        run_post_compact_hooks(thread_id=tid, messages=msgs, settings=st, out_events=events)
        assert len(events) >= 2
        assert all(str(e.get("type")) == "hook_chain_event" for e in events)
        assert any(
            e.get("hook") == "post_compact.persist_paper_sources"
            and e.get("phase") == "post_compact"
            for e in events
        )
        ent = get_session_for_thread(tid)
        assert ent.get("session_meta", {}).get("post_compact_paper_sources")
    finally:
        clear_session_store_for_tests()


def test_merge_hook_chain_preserves_existing_and_dedupes() -> None:
    ev = {
        "type": "hook_chain_event",
        "hook": "post_compact.persist_paper_sources",
        "phase": "post_compact",
        "ok": True,
        "detail": {"k": 1},
    }
    rm: dict = {"hook_chain_events": [dict(ev)]}
    merge_hook_chain_events_into_run_metadata(
        rm,
        extra_events=[dict(ev), dict(ev)],
        debug_events_tail=[dict(ev)],
    )
    assert len(rm["hook_chain_events"]) == 1


def test_merge_hook_chain_appends_distinct_events() -> None:
    a = {
        "type": "hook_chain_event",
        "hook": "a",
        "phase": "post_compact",
        "ok": True,
        "detail": {},
    }
    b = {
        "type": "hook_chain_event",
        "hook": "b",
        "phase": "subagent_start",
        "ok": True,
        "detail": {},
    }
    rm: dict = {}
    merge_hook_chain_events_into_run_metadata(rm, extra_events=[a], debug_events_tail=[b])
    assert len(rm["hook_chain_events"]) == 2
