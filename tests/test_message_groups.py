"""API-round grouping and tool integrity helpers (Epic A1)."""

from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from science_graphrag.agent.context.message_groups import (
    digest_window_as_messages_for_api_rounds,
    drop_oldest_api_round_groups,
    drop_oldest_digest_rounds_for_ptl,
    group_messages_by_api_round,
    tool_call_entry_id,
    validate_tool_message_integrity,
)


def test_group_messages_by_api_round_basic() -> None:
    messages = [
        HumanMessage(content="hi"),
        AIMessage(content="", tool_calls=[{"id": "c1", "name": "find_works", "args": {}}]),
        ToolMessage(content="{}", tool_call_id="c1", name="find_works"),
        AIMessage(content="done"),
    ]
    groups = group_messages_by_api_round(messages)
    assert len(groups) == 3
    assert isinstance(groups[0][0], HumanMessage)
    assert isinstance(groups[1][0], AIMessage)
    assert isinstance(groups[1][1], ToolMessage)
    assert isinstance(groups[2][0], AIMessage)


def test_tool_call_entry_id_accepts_dict_and_object() -> None:
    assert tool_call_entry_id({"id": "a"}) == "a"
    assert tool_call_entry_id(SimpleNamespace(id="b")) == "b"


def test_validate_tool_message_integrity_ok() -> None:
    messages = [
        AIMessage(
            content="",
            tool_calls=[{"id": "x1", "name": "t", "args": {}}],
        ),
        ToolMessage(content="ok", tool_call_id="x1", name="t"),
    ]
    assert not validate_tool_message_integrity(messages)


def test_validate_tool_message_integrity_orphan_tool() -> None:
    messages = [ToolMessage(content="{}", tool_call_id="orphan", name="t")]
    viol = validate_tool_message_integrity(messages)
    assert any("no preceding AIMessage" in v for v in viol)


def test_digest_window_maps_to_api_round_groups() -> None:
    digests = [
        {"user_intent": "a", "answer_excerpt": "1", "answer_class": "x", "tools_used": []},
        {"user_intent": "b", "answer_excerpt": "2", "answer_class": "x", "tools_used": []},
    ]
    msgs = digest_window_as_messages_for_api_rounds(digests)
    groups = group_messages_by_api_round(msgs)
    assert len(groups) >= 2
    assert isinstance(groups[0][0], HumanMessage)


def test_drop_oldest_digest_rounds_for_ptl_drops_oldest_digest() -> None:
    digests = [
        {"user_intent": "a", "answer_excerpt": "1", "answer_class": "x", "tools_used": []},
        {"user_intent": "b", "answer_excerpt": "2", "answer_class": "x", "tools_used": []},
        {"user_intent": "c", "answer_excerpt": "3", "answer_class": "x", "tools_used": []},
    ]
    out = drop_oldest_digest_rounds_for_ptl(list(digests), groups_to_drop=1)
    assert len(out) == 2
    assert out[0]["user_intent"] == "b"


def test_drop_oldest_api_round_groups_preserves_preamble() -> None:
    messages = [
        HumanMessage(content="sys"),
        AIMessage(content="a1"),
        AIMessage(content="a2"),
        AIMessage(content="a3"),
    ]
    out = drop_oldest_api_round_groups(messages, groups_to_drop=1)
    assert len(out) < len(messages)
    assert isinstance(out[0], HumanMessage)
