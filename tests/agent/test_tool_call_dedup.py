from __future__ import annotations

from science_graphrag.agent.tool_call_dedup import (
    normalize_unpaywall_doi,
    normalize_web_fetch_url,
    split_duplicate_external_fetch_calls,
)


def test_normalize_web_fetch_url_strips_fragment() -> None:
    a = normalize_web_fetch_url({"url": "https://Example.com/path#page"})
    b = normalize_web_fetch_url({"url": "https://example.com/path"})
    assert a == b


def test_split_duplicate_web_fetch_in_turn() -> None:
    url = "https://example.org/paper"
    state = {"metadata": {}}
    tcs = [
        {"name": "web_fetch", "id": "1", "args": {"url": url}},
        {"name": "web_fetch", "id": "2", "args": {"url": url}},
    ]
    kept, suppressed, patch = split_duplicate_external_fetch_calls(state=state, tool_calls=tcs)
    assert len(kept) == 1
    assert len(suppressed) == 1
    norm = normalize_web_fetch_url({"url": url})
    assert norm is not None
    assert norm in (patch.get("turn_web_fetch_urls") or [])


def test_split_duplicate_preserves_non_dict_tool_calls() -> None:
    tcs = ["legacy", {"name": "web_fetch", "id": "1", "args": {"url": "https://a.test/x"}}]
    kept, suppressed, _patch = split_duplicate_external_fetch_calls(state={"metadata": {}}, tool_calls=tcs)
    assert kept[0] == "legacy"
    assert len(kept) == 2
    assert not suppressed


def test_split_duplicate_unpaywall_doi() -> None:
    state = {"metadata": {}}
    tcs = [
        {"name": "unpaywall_lookup", "id": "1", "args": {"doi": "10.1000/xyz"}},
        {"name": "unpaywall_lookup", "id": "2", "args": {"doi": "10.1000/xyz"}},
    ]
    kept, suppressed, _patch = split_duplicate_external_fetch_calls(state=state, tool_calls=tcs)
    assert len(kept) == 1
    assert len(suppressed) == 1
    assert normalize_unpaywall_doi({"doi": "10.1000/xyz"}) == "10.1000/xyz"
