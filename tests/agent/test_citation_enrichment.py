"""Tests for citation passage hydration (Ask UI excerpts)."""

import json

from langchain_core.messages import ToolMessage

from science_graphrag.agent.citation_enrichment import (
    hydrate_citations_for_ui,
    merge_quote_candidates_into_citations,
)


def test_merge_single_quote_candidate_when_citation_has_no_chunk_key():
    citations = [{"work_id": "w1", "title": "Only title"}]
    quote_candidates = [{"work_id": "w1", "chunk_id": "fp-x", "quote_text": "Only hit for this work."}]
    merge_quote_candidates_into_citations(citations, quote_candidates)
    assert citations[0].get("excerpt") == "Only hit for this work."


def test_merge_quote_candidates_matches_chunk_id_from_paper_quote_search():
    """paper_quote_search stores chunk key under chunk_id, not chunk_fingerprint."""

    citations = [
        {
            "work_id": "w1",
            "chunk_fingerprint": "fp-a",
            "title": "Paper A",
        },
    ]
    quote_candidates = [
        {
            "work_id": "w1",
            "chunk_id": "fp-a",
            "quote_text": "Matched via chunk_id.",
        },
    ]
    merge_quote_candidates_into_citations(citations, quote_candidates)
    assert citations[0].get("excerpt") == "Matched via chunk_id."


def test_merge_quote_candidates_by_work_and_fingerprint():
    citations = [
        {
            "work_id": "w1",
            "chunk_fingerprint": "fp-a",
            "title": "Paper A",
        },
    ]
    quote_candidates = [
        {
            "work_id": "w1",
            "chunk_fingerprint": "fp-a",
            "quote_text": "Hello from retrieval.",
        },
    ]
    merge_quote_candidates_into_citations(citations, quote_candidates)
    assert citations[0].get("excerpt") == "Hello from retrieval."


def test_merge_skips_when_citation_already_has_excerpt():
    citations = [
        {
            "work_id": "w1",
            "chunk_fingerprint": "fp-a",
            "excerpt": "Keep me",
        },
    ]
    quote_candidates = [
        {
            "work_id": "w1",
            "chunk_fingerprint": "fp-a",
            "quote_text": "Wrong",
        },
    ]
    merge_quote_candidates_into_citations(citations, quote_candidates)
    assert citations[0].get("excerpt") == "Keep me"


def test_hydrate_binds_title_only_citations_via_inventory_and_paper_profile():
    """Writer-only traces (paper_profile + final_answer) often omit ``work_id`` on citations."""

    citations = [{"title": "Attention Is All You Need", "rank": 1}]
    inventory = {
        "paper_matches": [
            {"work_id": "wid-1", "title": "Attention Is All You Need"},
        ],
    }
    messages = [
        ToolMessage(
            content=json.dumps(
                {
                    "work_id": "wid-1",
                    "title": "Attention Is All You Need",
                    "authors": [{"name": "A"}],
                    "abstract": "We propose transformers.",
                }
            ),
            name="paper_profile",
            tool_call_id="tc1",
        ),
    ]
    out = hydrate_citations_for_ui(
        citations,
        quote_candidates=[],
        chunk_store=None,
        inventory=inventory,
        messages=messages,
        specialist_results=None,
    )
    assert out[0].get("work_id") == "wid-1"
    assert out[0].get("excerpt") == "We propose transformers."


def test_hydrate_falls_back_to_chunk_store():
    class FakeStore:
        def get_chunk_text_by_work_and_fingerprint(self, *, work_id: str, chunk_fingerprint: str):
            if work_id == "w2" and chunk_fingerprint == "fp-b":
                return "From Qdrant."
            return None

    citations = [{"work_id": "w2", "chunk_fingerprint": "fp-b"}]
    out = hydrate_citations_for_ui(
        citations,
        quote_candidates=[],
        chunk_store=FakeStore(),
    )
    assert out[0].get("excerpt") == "From Qdrant."


def test_hydrate_synthesizes_citations_from_quote_candidates_when_empty() -> None:
    out = hydrate_citations_for_ui(
        [],
        quote_candidates=[
            {
                "work_id": "w-q1",
                "chunk_id": "fp-q1",
                "quote_text": "Trade-off evidence.",
            }
        ],
        chunk_store=None,
    )
    assert out == [
        {
            "work_id": "w-q1",
            "chunk_id": "fp-q1",
            "excerpt": "Trade-off evidence.",
        }
    ]


def test_hydrate_synthesizes_citations_from_inventory_when_empty() -> None:
    out = hydrate_citations_for_ui(
        [],
        quote_candidates=[],
        chunk_store=None,
        inventory={
            "papers": [
                {
                    "work_id": "wid-graph",
                    "title": "Graph Coverage Paper",
                }
            ]
        },
    )
    assert out == [{"work_id": "wid-graph", "title": "Graph Coverage Paper"}]
