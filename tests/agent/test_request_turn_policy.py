"""Tests for per-request agent turn policy (web toggle, plan mode session hints)."""

from __future__ import annotations

from science_graphrag.agent.request_turn_policy import (
    build_agent_request_turn_context,
    compute_turn_tool_denylist,
    effective_web_research_user_enabled,
)
from science_graphrag.config import Settings


def test_effective_web_research_user_enabled_none_is_true() -> None:
    assert effective_web_research_user_enabled(None) is True
    assert effective_web_research_user_enabled(True) is True
    assert effective_web_research_user_enabled(False) is False


def test_compute_turn_tool_denylist_when_deploy_on_user_off() -> None:
    st = Settings.model_construct()
    assert compute_turn_tool_denylist(st, web_research_user_enabled=False) == [
        "web_fetch",
        "web_search",
    ]


def test_build_agent_request_turn_context_metadata_keys() -> None:
    st = Settings.model_construct()
    ctx = build_agent_request_turn_context(
        st,
        thread_id=None,
        web_research_enabled=False,
        agent_mode="agent",
    )
    assert ctx.turn_tool_denylist
    assert ctx.run_metadata_fragment.get("effective_web_research_tools") is False


def test_plan_mode_seeds_research_plan(monkeypatch) -> None:
    from science_graphrag.agent import request_turn_policy

    captured: dict[str, object] = {}

    def _fake_seed(thread_id: str | None, *, question: str | None = None) -> None:
        captured["thread_id"] = thread_id
        captured["question"] = question

    monkeypatch.setattr(request_turn_policy, "seed_research_plan_if_empty", _fake_seed)
    ctx = build_agent_request_turn_context(
        Settings.model_construct(),
        thread_id="thr_plan",
        question="Составь план",
        web_research_enabled=False,
        agent_mode="plan",
    )
    assert ctx.mode == "plan"
    assert captured == {"thread_id": "thr_plan", "question": "Составь план"}


def test_plan_mode_seed_is_visible_as_snapshot() -> None:
    from science_graphrag.agent.context.research_plan_session import (
        get_research_plan_snapshot_for_thread,
    )
    from science_graphrag.agent.context.session_store import clear_session_store_for_tests

    try:
        clear_session_store_for_tests()
        build_agent_request_turn_context(
            Settings.model_construct(),
            thread_id="thr_plan_seed_visible",
            question="Составь план исследования",
            web_research_enabled=False,
            agent_mode="plan",
        )
        plan = get_research_plan_snapshot_for_thread("thr_plan_seed_visible")
    finally:
        clear_session_store_for_tests()
    assert isinstance(plan, dict)
    assert len(plan.get("items") or []) == 3
    assert plan.get("ui_mode") == "outline"


def test_plan_mode_seed_localized_to_russian() -> None:
    from science_graphrag.agent.context.research_plan_session import (
        get_research_plan_snapshot_for_thread,
    )
    from science_graphrag.agent.context.session_store import clear_session_store_for_tests

    try:
        clear_session_store_for_tests()
        build_agent_request_turn_context(
            Settings.model_construct(),
            thread_id="thr_plan_seed_ru",
            question="Составь план исследования и найди источники",
            web_research_enabled=False,
            agent_mode="plan",
        )
        plan = get_research_plan_snapshot_for_thread("thr_plan_seed_ru")
    finally:
        clear_session_store_for_tests()
    assert isinstance(plan, dict)
    items = plan.get("items") or []
    assert isinstance(items, list) and items
    text = " ".join(str(x.get("content") or "") for x in items if isinstance(x, dict)).lower()
    assert "уточн" in text and "источник" in text


def test_agent_mode_web_followup_resets_plan_to_web_outline() -> None:
    from science_graphrag.agent.context.research_plan_session import (
        get_research_plan_snapshot_for_thread,
    )
    from science_graphrag.agent.context.session_store import clear_session_store_for_tests

    try:
        clear_session_store_for_tests()
        build_agent_request_turn_context(
            Settings.model_construct(),
            thread_id="thr_web_followup",
            question="Составь план исследования по объектному детектированию",
            web_research_enabled=False,
            agent_mode="plan",
        )
        build_agent_request_turn_context(
            Settings.model_construct(),
            thread_id="thr_web_followup",
            question="поищи в интернете",
            web_research_enabled=True,
            agent_mode="agent",
        )
        plan = get_research_plan_snapshot_for_thread("thr_web_followup")
    finally:
        clear_session_store_for_tests()
    assert isinstance(plan, dict)
    assert plan.get("ui_mode") == "outline"
    ids = [str(x.get("id") or "") for x in (plan.get("items") or []) if isinstance(x, dict)]
    assert ids[:2] == ["01_web_scope", "02_web_search"]
