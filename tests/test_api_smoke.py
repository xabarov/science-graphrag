"""Smoke tests for FastAPI (no live Neo4j/Qdrant required for /health)."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from science_graphrag.api import main as api_main
from science_graphrag.api.retrieval import GroundedAnswer


def _client() -> TestClient:
    return TestClient(api_main.app)


def test_health_endpoint() -> None:
    """Health endpoint returns service-ready payload."""

    client = _client()
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json().get("status") == "ok"


def test_works_list_endpoint_smoke(monkeypatch: Any) -> None:
    """Works list endpoint returns typed payload via API layer."""

    def _fake_list_works(*_args: Any, **_kwargs: Any) -> tuple[list[dict[str, Any]], int]:
        return (
            [
                {
                    "work_id": "w1",
                    "title": "Test work",
                    "year": 2024,
                    "doi": None,
                    "arxiv_id": None,
                    "venue": None,
                    "authors_preview": [],
                    "has_semantic_layer": False,
                },
            ],
            1,
        )

    monkeypatch.setattr(api_main.works_api, "list_works", _fake_list_works)
    client = _client()

    res = client.get("/v1/works?limit=20&offset=0")
    assert res.status_code == 200
    payload = res.json()
    assert payload["total"] == 1
    assert payload["items"][0]["work_id"] == "w1"


def test_work_detail_graph_chunks_smoke(monkeypatch: Any) -> None:
    """Work detail, graph, and chunks endpoints accept stable response shapes."""

    def _fake_get_work_detail(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {
            "work_id": "w1",
            "title": "Test work",
            "abstract": None,
            "year": 2024,
            "doi": None,
            "arxiv_id": None,
            "venue": None,
            "authors": [],
            "ingestion": {"document_id": "d1", "has_chunks": False, "has_semantic_layer": False},
        }

    def _fake_work_chunks(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {
            "items": [
                {
                    "document_id": "d1",
                    "chunk_fingerprint": "fp1",
                    "section_path": "intro",
                    "text": "chunk",
                    "order": 0,
                },
            ],
            "total": 1,
        }

    def _fake_work_graph_neighborhood(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {
            "work_id": "w1",
            "nodes": [{"id": "w1", "type": "Work", "label": "Test work"}],
            "edges": [],
            "meta": {"semantic_available": False},
        }

    monkeypatch.setattr(api_main.works_api, "get_work_detail", _fake_get_work_detail)
    monkeypatch.setattr(api_main.works_api, "work_chunks", _fake_work_chunks)
    monkeypatch.setattr(
        api_main.works_api, "work_graph_neighborhood", _fake_work_graph_neighborhood
    )
    client = _client()

    detail = client.get("/v1/works/w1")
    assert detail.status_code == 200
    assert detail.json()["ingestion"]["has_chunks"] is True

    graph = client.get("/v1/works/w1/graph")
    assert graph.status_code == 200
    assert graph.json()["meta"]["semantic_available"] is False

    chunks = client.get("/v1/works/w1/chunks?limit=10&offset=0")
    assert chunks.status_code == 200
    assert chunks.json()["total"] == 1


def test_query_endpoint_smoke(monkeypatch: Any) -> None:
    """Query endpoint returns answer with traceable citation fields."""

    def _fake_answer_query(*_args: Any, **_kwargs: Any) -> GroundedAnswer:
        return GroundedAnswer(
            answer="ok",
            citations=[
                {
                    "rank": 1,
                    "score": 0.1,
                    "work_id": "w1",
                    "document_id": "d1",
                    "chunk_fingerprint": "fp1",
                    "section_path": "intro",
                    "excerpt": "chunk",
                },
            ],
            graph_context={
                "methods": [],
                "datasets": [],
                "semantic_available": True,
                "context_work_id": "w1",
                "degraded": [],
                "error": None,
            },
            retrieval_trace={
                "embedding": {"embedding_model": "hash-deterministic", "vector_dim": 64},
                "hit_count": 1,
                "filter_work_id": None,
                "resolved_work_id": "w1",
                "qdrant_collection": "chunks",
                "top_k_requested": 3,
                "citations_returned": 1,
                "degraded": [],
            },
        )

    monkeypatch.setattr(api_main, "answer_query", _fake_answer_query)
    client = _client()

    res = client.post("/v1/query", json={"query": "test", "top_k": 3})
    assert res.status_code == 200
    payload = res.json()
    assert payload["answer"] == "ok"
    assert payload["citations"][0]["chunk_fingerprint"] == "fp1"
    assert payload["graph_context"]["semantic_available"] is True
    assert payload["retrieval_trace"]["qdrant_collection"] == "chunks"
    assert payload["retrieval_trace"]["citations_returned"] == 1


def test_benchmark_cases_list_smoke() -> None:
    """Benchmark UI: cases list returns fixtures from repo (no mocks)."""

    client = _client()
    res = client.get("/v1/benchmark/cases?limit=10&offset=0")
    assert res.status_code == 200
    payload = res.json()
    assert "items" in payload
    assert "total" in payload
    assert payload["total"] >= 1
    assert payload["items"][0]["case_id"]


def test_mandatory_happy_path_sequence_smoke(monkeypatch: Any) -> None:
    """Single-process chain: works list → work detail → chunks → query (mocked stores)."""

    def _fake_list_works(*_args: Any, **_kwargs: Any) -> tuple[list[dict[str, Any]], int]:
        row = {
            "work_id": "w_hp",
            "title": "Happy path work",
            "year": 2024,
            "doi": None,
            "arxiv_id": None,
            "venue": None,
            "authors_preview": [],
            "has_semantic_layer": True,
        }
        return ([row], 1)

    def _fake_get_work_detail(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {
            "work_id": "w_hp",
            "title": "Happy path work",
            "abstract": "Abstract",
            "year": 2024,
            "doi": None,
            "arxiv_id": None,
            "venue": None,
            "authors": [],
            "ingestion": {"document_id": "d_hp", "has_chunks": True, "has_semantic_layer": True},
        }

    def _fake_work_chunks(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {
            "items": [
                {
                    "document_id": "d_hp",
                    "chunk_fingerprint": "fp_hp",
                    "section_path": "intro",
                    "text": "body",
                    "order": 0,
                },
            ],
            "total": 1,
        }

    def _fake_answer_query(*_args: Any, **_kwargs: Any) -> GroundedAnswer:
        return GroundedAnswer(
            answer="ok",
            citations=[
                {
                    "rank": 1,
                    "score": 0.2,
                    "work_id": "w_hp",
                    "document_id": "d_hp",
                    "chunk_fingerprint": "fp_hp",
                    "section_path": "intro",
                    "excerpt": "body",
                },
            ],
            graph_context={
                "methods": ["m1"],
                "datasets": [],
                "semantic_available": True,
                "context_work_id": "w_hp",
                "degraded": [],
                "error": None,
            },
            retrieval_trace={
                "embedding": {"embedding_model": "t", "vector_dim": 4},
                "hit_count": 1,
                "filter_work_id": None,
                "resolved_work_id": "w_hp",
                "qdrant_collection": "chunks",
                "top_k_requested": 5,
                "citations_returned": 1,
                "degraded": [],
            },
        )

    monkeypatch.setattr(api_main.works_api, "list_works", _fake_list_works)
    monkeypatch.setattr(api_main.works_api, "get_work_detail", _fake_get_work_detail)
    monkeypatch.setattr(api_main.works_api, "work_chunks", _fake_work_chunks)
    monkeypatch.setattr(api_main, "answer_query", _fake_answer_query)

    client = _client()
    works = client.get("/v1/works?limit=5&offset=0")
    assert works.status_code == 200
    assert works.json()["items"][0]["work_id"] == "w_hp"

    detail = client.get("/v1/works/w_hp")
    assert detail.status_code == 200
    assert detail.json()["ingestion"]["has_chunks"] is True

    chunks = client.get("/v1/works/w_hp/chunks?limit=20&offset=0")
    assert chunks.status_code == 200
    assert chunks.json()["total"] == 1

    qres = client.post(
        "/v1/query",
        json={"query": "test happy path", "work_id": "w_hp", "top_k": 5},
    )
    assert qres.status_code == 200
    body = qres.json()
    assert body["citations"][0]["chunk_fingerprint"] == "fp_hp"
    assert body["retrieval_trace"]["resolved_work_id"] == "w_hp"
