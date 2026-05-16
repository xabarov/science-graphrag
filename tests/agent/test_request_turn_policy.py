"""Tests for per-request agent turn policy (web toggle, plan mode session hints)."""

from __future__ import annotations

from science_graphrag.agent.pdf_read_contract import PDF_READ_USER_MESSAGE_TOKEN
from science_graphrag.agent.request_turn_policy import (
    EXTERNAL_RESEARCH_TOOL_NAMES,
    build_agent_request_turn_context,
    compute_turn_tool_denylist,
    effective_web_research_user_enabled,
)
from science_graphrag.config import Settings


def test_effective_web_research_user_enabled_none_is_true() -> None:
    assert effective_web_research_user_enabled(None) is True
    assert effective_web_research_user_enabled(None, default_when_unspecified=False) is False
    assert effective_web_research_user_enabled(True) is True
    assert effective_web_research_user_enabled(False) is False


def test_compute_turn_tool_denylist_when_deploy_on_user_off() -> None:
    st = Settings.model_construct()
    assert compute_turn_tool_denylist(st, web_research_user_enabled=False) == sorted(
        EXTERNAL_RESEARCH_TOOL_NAMES
    )


def test_compute_turn_tool_denylist_web_off_allows_pdf_when_explicit() -> None:
    st = Settings.model_construct()
    deny = compute_turn_tool_denylist(
        st,
        web_research_user_enabled=False,
        explicit_pdf_read_request=True,
    )
    assert "read_external_pdf" not in deny
    assert "web_search" in deny


def test_compute_turn_tool_denylist_pdf_only_turn_blocks_web_tools() -> None:
    st = Settings.model_construct()
    deny = compute_turn_tool_denylist(
        st,
        web_research_user_enabled=True,
        explicit_pdf_read_request=True,
        explicit_pdf_only_turn=True,
    )
    assert "read_external_pdf" not in deny
    assert "web_fetch" in deny
    assert "web_search" in deny


def test_compute_turn_tool_denylist_pdf_mode_off_blocks_without_explicit() -> None:
    st = Settings.model_construct(pdf_reading_mode="off")
    deny = compute_turn_tool_denylist(
        st,
        web_research_user_enabled=True,
        explicit_pdf_read_request=False,
    )
    assert "read_external_pdf" in deny


def test_compute_turn_tool_denylist_pdf_mode_off_allows_explicit() -> None:
    st = Settings.model_construct(pdf_reading_mode="off")
    deny = compute_turn_tool_denylist(
        st,
        web_research_user_enabled=True,
        explicit_pdf_read_request=True,
    )
    assert "read_external_pdf" not in deny


def test_compute_turn_tool_denylist_operator_disables_pdf_tool() -> None:
    st = Settings.model_construct(agent_pdf_read_tool_enabled=False)
    deny = compute_turn_tool_denylist(
        st,
        web_research_user_enabled=True,
        explicit_pdf_read_request=True,
    )
    assert "read_external_pdf" in deny


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
    assert ctx.run_metadata_fragment.get("request_pdf_reading_mode") == "ask"
    assert ctx.run_metadata_fragment.get("agent_pdf_read_backend_mode") == "hybrid"


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


def test_agent_mode_arxiv_followup_resets_plan_to_arxiv_outline() -> None:
    from science_graphrag.agent.context.research_plan_session import (
        get_research_plan_snapshot_for_thread,
    )
    from science_graphrag.agent.context.session_store import clear_session_store_for_tests

    try:
        clear_session_store_for_tests()
        build_agent_request_turn_context(
            Settings.model_construct(),
            thread_id="thr_arxiv_followup",
            question="Составь план исследования по объектному детектированию",
            web_research_enabled=False,
            agent_mode="plan",
        )
        build_agent_request_turn_context(
            Settings.model_construct(),
            thread_id="thr_arxiv_followup",
            question="поищи препринты на arxiv",
            web_research_enabled=True,
            agent_mode="agent",
        )
        plan = get_research_plan_snapshot_for_thread("thr_arxiv_followup")
    finally:
        clear_session_store_for_tests()
    assert isinstance(plan, dict)
    ids = [str(x.get("id") or "") for x in (plan.get("items") or []) if isinstance(x, dict)]
    assert ids[:2] == ["01_arxiv_scope", "02_arxiv_search"]


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


def test_build_agent_request_turn_context_respects_persisted_external_default_off() -> None:
    st = Settings.model_construct(external_research_default_enabled=False)
    ctx = build_agent_request_turn_context(
        st,
        thread_id=None,
        web_research_enabled=None,
        agent_mode="agent",
    )
    assert ctx.run_metadata_fragment["effective_web_research_user_enabled"] is False
    assert "web_search" in ctx.turn_tool_denylist


def test_build_agent_request_turn_context_pdf_token_turn_denies_web_fetch() -> None:
    st = Settings.model_construct()
    ctx = build_agent_request_turn_context(
        st,
        thread_id=None,
        question=PDF_READ_USER_MESSAGE_TOKEN,
        web_research_enabled=True,
        agent_mode="agent",
        pdf_read_request={"pdf_url": "https://arxiv.org/pdf/1706.03762.pdf"},
    )
    assert "read_external_pdf" not in ctx.turn_tool_denylist
    assert "web_fetch" in ctx.turn_tool_denylist
