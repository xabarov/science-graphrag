"""Wave H §H1 regression: paper sources survive ``context_compacted`` boundary.

End-to-end contract this file pins:

1. After a turn that used ``paper_quote_search`` / ``idea_search``, the post-compact hook
   chain persists a deduped capsule of work_id-bearing rows under
   ``session_meta.post_compact_paper_sources``.
2. On the next user turn, ``format_user_with_memory`` re-injects those rows as a
   ``<paper_sources_restored>`` block so the agent does not lose grounding after a
   compact boundary.
3. The capsule is consumed once (one-shot restore) and cleared from session_meta.

This file is the operator-readable seam for "did paper evidence survive compaction?"
question. See also ``docs/analysis/agent-engine-and-benchmarks-next-waves-2026-05-09.md``
§6.1 H1.
"""

from __future__ import annotations

import json

from langchain_core.messages import ToolMessage

from science_graphrag.agent.context.post_compact_attachments import (
    clear_paper_sources_capsule,
    load_paper_sources_items,
)
from science_graphrag.agent.context.session_store import (
    clear_session_store_for_tests,
    format_user_with_memory,
    get_session_for_thread,
    update_session_after_turn,
)
from science_graphrag.agent.hooks import run_post_compact_hooks
from science_graphrag.config import Settings


def _seed_thread(tid: str) -> None:
    update_session_after_turn(
        tid,
        turn_digest={
            "user_intent": "What does the BERT paper say about masked LM?",
            "answer_excerpt": "It introduces masked language modeling.",
            "answer_class": "grounded_explanation",
            "tools_used": ["idea_search", "paper_quote_search"],
        },
    )


def _paper_messages_with_grounding() -> list[ToolMessage]:
    """Two ToolMessages that mirror a typical pre-compact paper evidence batch."""
    idea = ToolMessage(
        content=json.dumps(
            {
                "items": [
                    {
                        "work_id": "w-bert",
                        "snippet": "Pre-training of deep bidirectional transformers",
                    },
                    {
                        "work_id": "w-roberta",
                        "snippet": "A robustly optimized BERT pretraining approach",
                    },
                ]
            }
        ),
        tool_call_id="tc1",
        name="idea_search",
    )
    quote = ToolMessage(
        content=json.dumps(
            {
                "quote_candidates": [
                    {
                        "work_id": "w-bert",
                        "quote_text": "We introduce a new language representation model called BERT.",
                    },
                    {
                        "work_id": "w-bert-extra",
                        "quote_text": "Masked LM enables fine-tuned bidirectional context.",
                    },
                ]
            }
        ),
        tool_call_id="tc2",
        name="paper_quote_search",
    )
    return [idea, quote]


def test_full_lifecycle_paper_sources_restore() -> None:
    """End-to-end: persist after compact → load on next turn → inject into prompt → clear."""
    try:
        tid = "t_wave_h_paper_restore"
        _seed_thread(tid)

        settings = Settings.model_construct(
            agent_post_compact_paper_sources_enabled=True,
            agent_post_compact_paper_sources_max_items=12,
        )

        events: list[dict] = []
        decisions = run_post_compact_hooks(
            thread_id=tid,
            messages=_paper_messages_with_grounding(),
            settings=settings,
            out_events=events,
        )
        persist = next(d for d in decisions if d.hook_id == "post_compact.persist_paper_sources")
        assert persist.detail.get("post_compact_paper_sources_saved", 0) >= 3

        ent = get_session_for_thread(tid)
        loaded = load_paper_sources_items(ent)
        loaded_ids = {item.get("work_id") for item in loaded}
        assert {"w-bert", "w-roberta", "w-bert-extra"}.issubset(loaded_ids)
        sources = {item.get("source") for item in loaded}
        assert "idea_search" in sources and "paper_quote_search" in sources

        prompt = format_user_with_memory(
            question="follow-up: which paper introduced masked LM?",
            session_summary="prior recap",
            history_digest=[],
            paper_sources_items=loaded,
        )
        assert "<paper_sources_restored>" in prompt
        for wid in ("w-bert", "w-roberta", "w-bert-extra"):
            assert wid in prompt
        assert "follow-up: which paper introduced masked LM?" in prompt

        clear_paper_sources_capsule(tid)
        ent_after = get_session_for_thread(tid)
        assert not load_paper_sources_items(ent_after)
    finally:
        clear_session_store_for_tests()


def test_post_compact_disabled_yields_no_capsule() -> None:
    """Operator can suppress the capsule via ``agent_post_compact_paper_sources_enabled=False``."""
    try:
        tid = "t_wave_h_paper_restore_off"
        _seed_thread(tid)
        settings = Settings.model_construct(agent_post_compact_paper_sources_enabled=False)

        decisions = run_post_compact_hooks(
            thread_id=tid,
            messages=_paper_messages_with_grounding(),
            settings=settings,
        )
        persist = next(d for d in decisions if d.hook_id == "post_compact.persist_paper_sources")
        assert persist.detail.get("post_compact_paper_sources_saved", 0) == 0

        ent = get_session_for_thread(tid)
        assert not load_paper_sources_items(ent)
    finally:
        clear_session_store_for_tests()


def test_persist_dedupes_repeated_work_ids_across_tools() -> None:
    """A work_id seen via both idea_search and paper_quote_search must persist once."""
    try:
        tid = "t_wave_h_paper_restore_dedup"
        _seed_thread(tid)
        settings = Settings.model_construct(
            agent_post_compact_paper_sources_enabled=True,
            agent_post_compact_paper_sources_max_items=12,
        )

        msgs = [
            ToolMessage(
                content=json.dumps({"items": [{"work_id": "w-shared", "snippet": "first"}]}),
                tool_call_id="tc-a",
                name="idea_search",
            ),
            ToolMessage(
                content=json.dumps(
                    {"quote_candidates": [{"work_id": "w-shared", "quote_text": "second variant"}]}
                ),
                tool_call_id="tc-b",
                name="paper_quote_search",
            ),
        ]
        run_post_compact_hooks(thread_id=tid, messages=msgs, settings=settings)
        loaded = load_paper_sources_items(get_session_for_thread(tid))
        assert [item.get("work_id") for item in loaded] == ["w-shared"]
    finally:
        clear_session_store_for_tests()


def test_paper_sources_restore_count_visible_via_session_meta() -> None:
    """After persist, ``post_compact_paper_sources`` capsule is visible in session_meta.

    This is the seam consumed by ``science_graphrag/agent/graph/state.py`` to populate
    ``run_metadata.post_compact_paper_sources_restored_count`` on the next turn — the
    operator-facing signal that paper grounding survived compaction.
    """
    try:
        tid = "t_wave_h_paper_restore_meta"
        _seed_thread(tid)
        settings = Settings.model_construct(
            agent_post_compact_paper_sources_enabled=True,
            agent_post_compact_paper_sources_max_items=12,
        )
        run_post_compact_hooks(
            thread_id=tid,
            messages=_paper_messages_with_grounding(),
            settings=settings,
        )
        ent = get_session_for_thread(tid)
        capsule = (ent.get("session_meta") or {}).get("post_compact_paper_sources")
        assert isinstance(capsule, dict)
        items = capsule.get("items") or []
        assert len(items) >= 3
        # Each item must have at least one of work_id / snippet — operator must be able to
        # tell what evidence is being restored, not just that "something" was saved.
        for item in items:
            assert item.get("work_id") or item.get("snippet")
    finally:
        clear_session_store_for_tests()
