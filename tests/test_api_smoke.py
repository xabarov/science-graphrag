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
            graph_context={"methods": [], "datasets": []},
            retrieval_trace={
                "embedding": {"embedding_model": "hash-deterministic", "vector_dim": 64}
            },
        )

    monkeypatch.setattr(api_main, "answer_query", _fake_answer_query)
    client = _client()

    res = client.post("/v1/query", json={"query": "test", "top_k": 3})
    assert res.status_code == 200
    payload = res.json()
    assert payload["answer"] == "ok"
    assert payload["citations"][0]["chunk_fingerprint"] == "fp1"
