"""Smoke tests for FastAPI (no live Neo4j/Qdrant required for /health)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from science_graphrag.api import benchmark as benchmark_api
from science_graphrag.api import main as api_main
from science_graphrag.api.retrieval import GroundedAnswer
from science_graphrag.api.task_store import BenchmarkTaskStore, RunPayloadTooLargeError


def _client() -> TestClient:
    return TestClient(api_main.app)


def test_health_endpoint() -> None:
    """Health endpoint returns service-ready payload."""

    client = _client()
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json().get("status") == "ok"


def test_root_redirects_to_ui_when_built() -> None:
    """Root path should send browsers to the SPA shell instead of the legacy MVP page."""

    client = _client()
    res = client.get("/", follow_redirects=False)
    assert res.status_code == 307
    assert res.headers["location"] == "/ui/"


def test_legacy_retrieval_mvp_page_smoke() -> None:
    """Legacy retrieval MVP remains available on an explicit route."""

    client = _client()
    res = client.get("/legacy/retrieval-mvp")
    assert res.status_code == 200
    assert "Grounded query (MVP)" in res.text


def test_settings_schema_endpoint_smoke() -> None:
    """Settings schema is available for the new settings UI."""

    client = _client()
    res = client.get("/v1/settings/schema")
    assert res.status_code == 200
    payload = res.json()
    assert payload["version"] >= 1
    assert payload["sections"][0]["id"] == "llm"
    section_ids = {s["id"] for s in payload["sections"]}
    assert "ingestion" in section_ids
    ingest = next(s for s in payload["sections"] if s["id"] == "ingestion")
    assert ingest["fields"][0]["id"] == "max_file_size_mb"


def test_settings_snapshot_endpoint_smoke() -> None:
    """Settings snapshot returns masked LLM state and section catalog."""

    client = _client()
    res = client.get("/v1/settings")
    assert res.status_code == 200
    payload = res.json()
    assert any(item["id"] == "llm" for item in payload["sections"])
    assert "status" in payload["llm"]
    assert "effective" in payload["llm"]
    assert "ingestion" in payload
    assert payload["ingestion"]["effective"]["resolved_max_file_size_mb"] >= 1
    assert "diagnostics" in payload and "app_version" in payload["diagnostics"]
    assert "security" in payload and "settings_auth_required" in payload["security"]
    assert "has_saved_secret" in payload["llm"]["status"]
    assert "secret_source" in payload["llm"]["status"]


def test_settings_service_llm_snapshot_env_secret_only(tmp_path: Path) -> None:
    """LLM snapshot reflects environment API key when vault is empty."""

    from science_graphrag.config import Settings
    from science_graphrag.settings.repository import SettingsRepository
    from science_graphrag.settings.secrets import SecretStore
    from science_graphrag.settings.service import SettingsService

    service = SettingsService(
        repo_root=tmp_path,
        repository=SettingsRepository(tmp_path),
        secret_store=SecretStore(tmp_path),
    )
    base = Settings(extraction_llm_api_key="sk-env-12345678901234567890")
    snap = service.get_snapshot(base)
    st = snap.llm["status"]
    assert st["secret_source"] == "environment"
    assert st["has_saved_secret"] is False
    assert st["configured"] is True
    assert st["masked_key"]


def test_settings_ingestion_patch_smoke(tmp_path: Path, monkeypatch: Any) -> None:
    """Settings API persists workspace upload size limit."""

    from science_graphrag.api import settings as settings_api
    from science_graphrag.settings.repository import SettingsRepository
    from science_graphrag.settings.secrets import SecretStore
    from science_graphrag.settings.service import SettingsService

    service = SettingsService(
        repo_root=tmp_path,
        repository=SettingsRepository(tmp_path),
        secret_store=SecretStore(tmp_path),
    )
    monkeypatch.setattr(settings_api, "_SETTINGS_SERVICE", service)

    client = _client()
    patch_res = client.patch("/v1/settings/ingestion", json={"max_file_size_mb": 96})
    assert patch_res.status_code == 200
    body = patch_res.json()
    assert body["ingestion"]["max_file_size_mb"] == 96
    assert body["ingestion"]["effective"]["resolved_max_file_size_mb"] == 96


def test_settings_llm_patch_and_delete_secret_smoke(tmp_path: Path, monkeypatch: Any) -> None:
    """Settings API persists non-secret values and masks stored API key."""

    from science_graphrag.api import settings as settings_api
    from science_graphrag.settings.repository import SettingsRepository
    from science_graphrag.settings.secrets import SecretStore
    from science_graphrag.settings.service import SettingsService

    service = SettingsService(
        repo_root=tmp_path,
        repository=SettingsRepository(tmp_path),
        secret_store=SecretStore(tmp_path),
    )
    monkeypatch.setattr(settings_api, "_SETTINGS_SERVICE", service)

    client = _client()
    patch_res = client.patch(
        "/v1/settings/llm",
        json={
            "base_url": "https://openrouter.ai/api/v1",
            "model": "mistralai/mistral-small-3.2-24b-instruct",
            "temperature": 0.1,
            "timeout_seconds": 120,
            "api_key": "sk-demo-secret",
        },
    )
    assert patch_res.status_code == 200
    body = patch_res.json()
    assert body["llm"]["status"]["configured"] is True
    assert body["llm"]["status"]["has_saved_secret"] is True
    assert body["llm"]["status"]["secret_source"] == "server_managed"
    assert body["llm"]["status"]["masked_key"].startswith("sk-d")
    assert body["llm"]["effective"]["resolved_model"] == "mistralai/mistral-small-3.2-24b-instruct"

    delete_res = client.delete("/v1/settings/llm/secret")
    assert delete_res.status_code == 200
    deleted = delete_res.json()
    assert deleted["llm"]["status"]["has_saved_secret"] is False
    assert deleted["llm"]["status"]["secret_source"] in ("none", "environment")
    if deleted["llm"]["status"]["secret_source"] == "none":
        assert deleted["llm"]["status"]["configured"] is False
    else:
        assert deleted["llm"]["status"]["configured"] is True
    assert "ingestion" in deleted


def test_workspace_upload_rejects_oversized_file(monkeypatch: Any) -> None:
    """POST .../ingest/document returns 413 when file exceeds configured limit."""

    from science_graphrag.api import workspaces as ws_api
    from science_graphrag.config import Settings

    class _FakeStore:
        def workspace_get(self, workspace_id: str) -> dict[str, Any] | None:
            if workspace_id == "ws-upload":
                return {"id": workspace_id, "name": "U", "work_ids": []}
            return None

        def close(self) -> None:
            return None

    monkeypatch.setattr(ws_api, "_store", lambda _settings: _FakeStore())

    limited = Settings().model_copy(update={"workspace_upload_max_file_size_mb": 1})
    client = _client()
    # Must match the callable captured on the route (``workspaces`` import), not
    # ``science_graphrag.config.get_settings`` after conftest wraps the latter.
    dep = ws_api.get_settings
    client.app.dependency_overrides[dep] = lambda: limited
    try:
        two_mb = b"x" * (2 * 1024 * 1024)
        res = client.post(
            "/v1/workspaces/ws-upload/ingest/document",
            files={"file": ("big.pdf", two_mb, "application/pdf")},
        )
    finally:
        client.app.dependency_overrides.pop(dep, None)

    assert res.status_code == 413
    detail = res.json()["detail"]
    assert detail["error"] == "workspace_upload_file_too_large"
    assert detail["max_file_size_mb"] == 1


def test_settings_llm_test_uses_service_result(tmp_path: Path, monkeypatch: Any) -> None:
    """Connection test returns structured service payload to UI."""

    from science_graphrag.api import settings as settings_api
    from science_graphrag.settings.repository import SettingsRepository
    from science_graphrag.settings.secrets import SecretStore
    from science_graphrag.settings.service import SettingsService

    service = SettingsService(
        repo_root=tmp_path,
        repository=SettingsRepository(tmp_path),
        secret_store=SecretStore(tmp_path),
    )

    def _fake_test(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {
            "status": "connected",
            "message": "OK",
            "latency_ms": 12,
            "resolved": {
                "base_url": "https://openrouter.ai/api/v1",
                "model": "demo/model",
                "timeout_seconds": 30,
                "temperature": 0.0,
                "used_saved_secret": False,
            },
        }

    monkeypatch.setattr(service, "test_llm_connection", _fake_test)
    monkeypatch.setattr(settings_api, "_SETTINGS_SERVICE", service)

    client = _client()
    res = client.post(
        "/v1/settings/llm/test",
        json={
            "base_url": "https://openrouter.ai/api/v1",
            "model": "demo/model",
            "api_key": "sk-demo",
            "use_saved_secret": False,
        },
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["status"] == "connected"
    assert payload["resolved"]["model"] == "demo/model"


def test_workspaces_list_smoke(monkeypatch: Any) -> None:
    """GET /v1/workspaces lists Neo4j-backed workspaces (mocked store)."""

    from science_graphrag.api import workspaces as ws_api

    class _FakeStore:
        def workspace_list(self) -> list[dict[str, Any]]:
            return [{"id": "ws-1", "name": "Lab", "created_at": "2020-01-01T00:00:00+00:00", "work_ids": ["w-a"]}]

        def close(self) -> None:
            return None

    monkeypatch.setattr(ws_api, "_store", lambda _settings: _FakeStore())
    client = _client()
    res = client.get("/v1/workspaces")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == "ws-1"
    assert body["items"][0]["work_ids"] == ["w-a"]


def test_ingest_stubs_and_job_lookup() -> None:
    """Legacy ingest entrypoints stay stubbed; job status is 404 for unknown ids."""

    client = _client()
    assert client.post("/v1/ingest/arxiv", json={"arxiv_id": "1234.5678"}).status_code == 501
    assert client.post("/v1/ingest/doi", json={"doi": "10.1000/xyz"}).status_code == 501
    assert client.post("/v1/ingest/pdf").status_code == 501
    assert client.get("/v1/ingest/jobs/00000000-0000-0000-0000-000000000000").status_code == 404


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
            "nodes": [
                {"id": "w1", "type": "Work", "label": "Test work"},
                {"id": "n2", "type": "Work", "label": "Neighbor"},
            ],
            "edges": [{"source": "n2", "target": "w1", "type": "CITES"}],
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
    graph_body = graph.json()
    assert graph_body["meta"]["semantic_available"] is False
    assert graph_body["nodes"][0]["id"] == "w1"
    assert graph_body["nodes"][0]["label"] == "Test work"
    assert len(graph_body["edges"]) == 1
    assert graph_body["edges"][0]["source"] == "n2"
    assert graph_body["edges"][0]["target"] == "w1"

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
                "top_hit_scores": [0.1],
                "query_preview": "test",
                "retrieval_policy": "section_boost_v1;back_matter_deprioritized;oversample_then_top_k",
                "answer_synthesis": {
                    "mode": "deterministic_snippets",
                    "second_stage_llm": False,
                },
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
    assert payload["retrieval_trace"]["answer_synthesis"]["second_stage_llm"] is False
    assert "retrieval_policy" in payload["retrieval_trace"]


def test_post_query_accepts_workspace_id_unknown_workspace(monkeypatch: Any) -> None:
    """POST /v1/query with workspace_id (no work_id) does not 500 when workspace is unknown."""

    from science_graphrag.api import retrieval as retr_mod

    def _fake_ws_scope(_settings: Any, workspace_id: str) -> tuple[list[str], dict[str, Any]]:
        return [], {
            "workspace_id": workspace_id.strip(),
            "workspace_missing": True,
            "workspace_scope_work_count": 0,
        }

    monkeypatch.setattr(retr_mod, "_workspace_scope_work_ids", _fake_ws_scope)
    client = _client()
    res = client.post(
        "/v1/query",
        json={"query": "hello workspace corpus", "workspace_id": "missing-ws-uuid", "top_k": 3},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["retrieval_trace"]["workspace_id"] == "missing-ws-uuid"
    assert body["retrieval_trace"].get("workspace_missing") is True
    assert body["retrieval_trace"].get("workspace_scope_work_count") == 0


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


def test_benchmark_cases_layer1_fixture_exists_on_disk() -> None:
    """Guard docker image inputs: benchmark fixtures must exist in repo for API discovery."""

    repo_root = Path(__file__).resolve().parents[1]
    fixture = repo_root / "tests" / "fixtures" / "benchmarks" / "layer1" / "yolov1" / "gold.json"
    assert fixture.is_file()


def test_benchmark_cases_layer2_list_smoke() -> None:
    """Benchmark UI: layer-2 fixtures listable."""

    client = _client()
    res = client.get("/v1/benchmark/cases?family=layer2&tier=merge_safe&limit=20")
    assert res.status_code == 200
    payload = res.json()
    assert payload["total"] >= 1
    assert payload["items"][0]["family"] == "layer2"
    assert payload["items"][0]["has_semantic_gold"] in (0, 1)


def test_benchmark_cases_graph_family_list_smoke() -> None:
    """Graph-v1 catalog: layer-1 fixtures that define graph_expectations."""

    client = _client()
    res = client.get("/v1/benchmark/cases?family=graph&limit=50")
    assert res.status_code == 200
    payload = res.json()
    assert payload["total"] >= 1
    assert payload["items"][0]["family"] == "graph"
    assert payload["items"][0]["has_graph_expectations"] == 1


def test_benchmark_models_list_smoke() -> None:
    client = _client()
    res = client.get("/v1/benchmark/models")
    assert res.status_code == 200
    payload = res.json()
    assert payload["total"] >= 3
    env_default = next(item for item in payload["items"] if item["profile_id"] == "env_default")
    assert env_default["label"]
    assert "layer1" in env_default["family_support"]
    student = next(item for item in payload["items"] if item["profile_id"] == "student_mistral_small_32")
    assert student["default_gold_source"] == "teacher_gold"
    assert student["default_threshold_profile"] == "student_mistral"


def test_benchmark_post_run_rejects_graph_family() -> None:
    client = _client()
    res = client.post(
        "/v1/benchmark/runs",
        json={"case_ids": ["yolov1"], "label": "x", "family": "graph"},
    )
    assert res.status_code == 400
    assert res.json().get("detail") == "graph_benchmark_use_cli"


def test_benchmark_case_layer2_detail_smoke() -> None:
    """Layer-2 case detail returns semantic gold as gold payload."""

    client = _client()
    res = client.get("/v1/benchmark/cases/no_llm_smoke?family=layer2")
    assert res.status_code == 200
    body = res.json()
    assert body["case_id"] == "no_llm_smoke"
    assert "expected_method_names_normalized" in body["gold"]


def test_benchmark_case_artifacts_layer1_smoke() -> None:
    """Artifact inventory for a layer-1 fixture (curated + teacher slots)."""

    client = _client()
    res = client.get("/v1/benchmark/cases/yolov1/artifacts?family=layer1")
    assert res.status_code == 200
    body = res.json()
    assert body["case_id"] == "yolov1"
    assert body["family"] == "layer1"
    assert body["article"]["present"] is True
    assert body["article"]["path_relative_to_repo"]
    variants = {v["id"]: v for v in body["gold_variants"]}
    assert set(variants) == {"curated_gold", "teacher_gold"}
    assert variants["curated_gold"]["present"] is True
    assert variants["curated_gold"]["filename"] == "gold.json"
    assert body["semantic_gold"] is None
    assert body["semantic_gold_teacher"] is None


def test_benchmark_case_artifacts_layer2_smoke() -> None:
    """Artifact inventory for layer-2 semantic fixture."""

    client = _client()
    res = client.get("/v1/benchmark/cases/no_llm_smoke/artifacts?family=layer2")
    assert res.status_code == 200
    body = res.json()
    assert body["family"] == "layer2"
    assert body["semantic_gold"]["present"] is True
    assert body["semantic_gold"]["path_relative_to_repo"]
    assert body["gold_variants"] == []


def test_benchmark_case_artifacts_graph_family_smoke() -> None:
    """Graph catalog uses same fixture tree but family=graph in the payload."""

    client = _client()
    res = client.get("/v1/benchmark/cases/yolov1/artifacts?family=graph")
    assert res.status_code == 200
    body = res.json()
    assert body["family"] == "graph"
    assert body["graph_expectations"] is True


def test_benchmark_run_summary_smoke(monkeypatch: Any) -> None:
    def _fake_get_run_summary(_run_id: str) -> dict[str, Any]:
        return {
            "run_id": "run-sum-1",
            "label": "l",
            "benchmark_family": "layer1",
            "status": "completed",
            "created_at": "t0",
            "started_at": "t1",
            "completed_at": "t2",
            "error_message": None,
            "run_config": {},
            "progress": {"total": 1, "completed": 1},
            "summary": {"pass_count": 1, "fail_count": 0, "case_count": 1},
            "cases": [
                {
                    "case_id": "yolov1",
                    "status": "ok",
                    "error_message": None,
                    "finished_at": "t3",
                    "summary": {"passed": True, "failed_checks": []},
                },
            ],
        }

    monkeypatch.setattr(benchmark_api.task_store, "get_run_summary", _fake_get_run_summary)
    client = _client()
    res = client.get("/v1/benchmark/runs/run-sum-1/summary")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["run_id"] == "run-sum-1"
    assert data["cases"][0]["case_id"] == "yolov1"
    assert "result" not in data["cases"][0]


def test_benchmark_run_summary_not_found(monkeypatch: Any) -> None:
    monkeypatch.setattr(benchmark_api.task_store, "get_run_summary", lambda _rid: None)
    assert _client().get("/v1/benchmark/runs/missing-run/summary").status_code == 404


def test_benchmark_get_run_payload_too_large(monkeypatch: Any) -> None:
    def _boom(_rid: str) -> Any:
        raise RunPayloadTooLargeError("run_payload_too_large_use_cases_api")

    monkeypatch.setattr(benchmark_api.task_store, "get_run", _boom)
    res = _client().get("/v1/benchmark/runs/any-id")
    assert res.status_code == 413
    assert res.json().get("detail") == "run_payload_too_large_use_cases_api"


def _fake_run_list_rows() -> list[dict[str, Any]]:
    base_summary = {
        "avg_names_f1": 0.0,
        "avg_sample_arxiv_f1": 0.0,
        "avg_sample_doi_f1": 0.0,
        "avg_layer2_recall_ratio": 0.0,
        "pass_count": 0,
        "fail_count": 0,
        "cancelled_count": 0,
        "case_count": 1,
    }
    return [
        {
            "run_id": "run-layer1",
            "label": "alpha",
            "benchmark_family": "layer1",
            "status": "completed",
            "created_at": "2025-01-02T00:00:00+00:00",
            "started_at": None,
            "completed_at": None,
            "run_config": {},
            "progress": {"total": 1, "completed": 1, "percent": 100.0},
            "summary": dict(base_summary),
        },
        {
            "run_id": "run-layer2-beta",
            "label": "beta",
            "benchmark_family": "layer2",
            "status": "running",
            "created_at": "2025-01-03T00:00:00+00:00",
            "started_at": None,
            "completed_at": None,
            "run_config": {},
            "progress": {"total": 1, "completed": 0, "percent": 0.0},
            "summary": dict(base_summary),
        },
    ]


def test_benchmark_list_runs_filters_family(monkeypatch: Any) -> None:
    monkeypatch.setattr(benchmark_api.task_store, "list_runs_summary", _fake_run_list_rows)
    res = _client().get("/v1/benchmark/runs", params={"family": "layer2"})
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["run_id"] == "run-layer2-beta"


def test_benchmark_list_runs_filters_q(monkeypatch: Any) -> None:
    monkeypatch.setattr(benchmark_api.task_store, "list_runs_summary", _fake_run_list_rows)
    res = _client().get("/v1/benchmark/runs", params={"q": "beta"})
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["run_id"] == "run-layer2-beta"


def test_benchmark_graph_snapshot_preview_smoke() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sample_path = repo_root / "eval/results/local-graph-yolov1.json"
    sample = json.loads(sample_path.read_text(encoding="utf-8"))
    res = _client().post(
        "/v1/benchmark/cases/yolov1/graph-snapshot-preview?family=graph",
        json={"graph_snapshot": sample},
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert "rows" in data
    assert data.get("opened_case_id") == "yolov1"
    assert data.get("case_id_mismatch") is False


def test_benchmark_runs_compare_smoke(monkeypatch: Any) -> None:
    def _make_run(rid: str, names_f1: float) -> dict[str, Any]:
        return {
            "run_id": rid,
            "benchmark_family": "layer1",
            "label": rid,
            "run_config": {"model_profile": "a" if names_f1 >= 1.0 else "b"},
            "cases": [
                {
                    "case_id": "yolov1",
                    "status": "ok",
                    "result": {
                        "metrics": {
                            "contract": {"passed": True, "checks": {}},
                            "authorships": {"names_f1": names_f1},
                            "references": {"sample_arxiv_f1": 0.5},
                        },
                    },
                },
            ],
        }

    runs = {
        "run-base": _make_run("run-base", 1.0),
        "run-curr": _make_run("run-curr", 0.5),
    }

    def _fake_get_run(rid: str) -> dict[str, Any] | None:
        return runs.get(rid)

    monkeypatch.setattr(benchmark_api.task_store, "get_run", _fake_get_run)
    client = _client()
    res = client.get(
        "/v1/benchmark/runs/compare",
        params={"baseline_run_id": "run-base", "current_run_id": "run-curr"},
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["summary"]["regression_count"] >= 1
    assert any(r.get("metric") == "authorships.names_f1" for r in data["regressions"])
    assert isinstance(data.get("markdown"), str)
    assert "Benchmark report compare" in data["markdown"]
    assert "run-base" in data["markdown"]


def test_benchmark_runs_compare_case_limit(monkeypatch: Any) -> None:
    big_cases = [
        {"case_id": f"c{i}", "status": "ok", "result": {"metrics": {"contract": {"passed": True}}}}
        for i in range(2001)
    ]

    def _fake_get_run(rid: str) -> dict[str, Any] | None:
        return {"run_id": rid, "benchmark_family": "layer1", "cases": big_cases}

    monkeypatch.setattr(benchmark_api.task_store, "get_run", _fake_get_run)
    res = _client().get(
        "/v1/benchmark/runs/compare",
        params={"baseline_run_id": "big-a", "current_run_id": "big-b"},
    )
    assert res.status_code == 400
    assert res.json().get("detail") == "compare_case_limit_exceeded"


def test_benchmark_runs_compare_family_mismatch(monkeypatch: Any) -> None:
    def _fake_get_run(rid: str) -> dict[str, Any]:
        if rid == "a":
            return {"run_id": "a", "benchmark_family": "layer1", "cases": []}
        return {"run_id": "b", "benchmark_family": "layer2", "cases": []}

    monkeypatch.setattr(benchmark_api.task_store, "get_run", _fake_get_run)
    res = _client().get(
        "/v1/benchmark/runs/compare",
        params={"baseline_run_id": "a", "current_run_id": "b"},
    )
    assert res.status_code == 400
    assert res.json().get("detail") == "benchmark_family_mismatch"


def test_benchmark_post_run_accepts_model_fields(monkeypatch: Any) -> None:
    captured: dict[str, Any] = {}

    def _fake_create_run(**kwargs: Any) -> str:
        captured.update(kwargs)
        return "run-test-1"

    def _fake_get_run(run_id: str) -> dict[str, Any]:
        return {
            "run_id": run_id,
            "status": "running",
            "benchmark_family": "layer1",
            "label": "student-run",
            "run_config": {
                "model_profile": "student_mistral_small_32",
                "resolved_model_id": "mistralai/mistral-small-3.2-24b-instruct",
                "gold_source": "teacher_gold",
                "threshold_profile": "student_mistral",
            },
        }

    monkeypatch.setattr(benchmark_api.task_store, "create_run", _fake_create_run)
    monkeypatch.setattr(benchmark_api.task_store, "get_run", _fake_get_run)
    client = _client()
    res = client.post(
        "/v1/benchmark/runs",
        json={
            "case_ids": ["yolov1"],
            "label": "student-run",
            "family": "layer1",
            "model_profile": "student_mistral_small_32",
            "gold_source": "teacher_gold",
            "threshold_profile": "student_mistral",
        },
    )
    assert res.status_code == 200
    assert res.json()["run_id"] == "run-test-1"
    assert res.json()["benchmark_family"] == "layer1"
    assert res.json()["run_config"]["resolved_model_id"] == "mistralai/mistral-small-3.2-24b-instruct"
    assert res.json()["run_config"]["gold_source"] == "teacher_gold"
    assert captured["benchmark_family"] == "layer1"
    assert captured["run_config"]["model_profile"] == "student_mistral_small_32"
    assert captured["run_config"]["gold_source"] == "teacher_gold"
    assert captured["run_config"]["threshold_profile"] == "student_mistral"


def test_benchmark_post_run_returns_human_validation_errors(monkeypatch: Any) -> None:
    def _fake_create_run(**_kwargs: Any) -> str:
        raise ValueError("custom_model_id_required")

    monkeypatch.setattr(benchmark_api.task_store, "create_run", _fake_create_run)
    client = _client()
    res = client.post(
        "/v1/benchmark/runs",
        json={
            "case_ids": ["yolov1"],
            "family": "layer1",
            "model_profile": "custom",
        },
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "custom_model_id_required"


def test_benchmark_run_cases_page_smoke(monkeypatch: Any) -> None:
    def _fake_page(
        _run_id: str,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> dict[str, Any]:
        return {
            "run_id": "run-page",
            "benchmark_family": "layer1",
            "total": 2,
            "offset": offset,
            "limit": limit,
            "items": [
                {
                    "case_id": "c1",
                    "status": "ok",
                    "summary": {"names_f1": 1.0},
                    "error_message": None,
                    "finished_at": "t",
                },
            ],
        }

    monkeypatch.setattr(benchmark_api.task_store, "get_run_cases_page", _fake_page)
    client = _client()
    res = client.get("/v1/benchmark/runs/run-page/cases?offset=0&limit=50")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["total"] == 2
    assert len(data["items"]) == 1
    assert data["items"][0]["case_id"] == "c1"


def test_benchmark_run_case_detail_smoke(monkeypatch: Any) -> None:
    def _fake_get_run(_run_id: str) -> dict[str, Any]:
        return {
            "run_id": "run-atss",
            "benchmark_family": "layer1",
            "run_config": {
                "gold_source": "teacher_gold",
                "model_profile": "student_mistral_small_32",
            },
            "cases": [
                {
                    "case_id": "atss_realpdf",
                    "status": "ok",
                    "summary": {"passed": True, "failed_checks": []},
                    "result": {
                        "metrics": {
                            "contract": {"passed": True, "checks": {}},
                            "authorships": {"names_f1": 1.0},
                            "references": {"sample_arxiv_f1": 1.0, "sample_doi_f1": 1.0},
                        },
                        "predicted": {
                            "work_metadata": {"title": "ATSS"},
                            "authorships": [],
                            "references": [],
                        },
                        "gold": {
                            "work_metadata": {"title": "ATSS"},
                            "authorships": [],
                            "references": {"expected_count": 0},
                        },
                        "diagnostics": {"metadata_source": "llm"},
                    },
                },
            ],
        }

    monkeypatch.setattr(benchmark_api.task_store, "get_run", _fake_get_run)
    client = _client()
    res = client.get("/v1/benchmark/runs/run-atss/cases/atss_realpdf")
    assert res.status_code == 200
    payload = res.json()["data"]
    assert payload["case_id"] == "atss_realpdf"
    assert payload["gold"]["source"] == "teacher_gold"
    assert payload["article"]["raw_markdown"]
    assert "metadata_rows" in payload["comparison"]


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
                "answer_synthesis": {"mode": "x", "second_stage_llm": False},
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


def test_benchmark_runs_api_lists_restored_store(monkeypatch: Any, tmp_path: Path) -> None:
    """API GET /v1/benchmark/runs sees runs loaded from disk on a fresh BenchmarkTaskStore (Wave E3)."""

    hist = tmp_path / "br_hist"
    hist.mkdir()

    def _fake_layer1_runner(
        fixture_dir: Path,
        *,
        settings: Any,
        external_gold_root=None,
        gold_filename: str = "gold.json",
        threshold_profile: str | None = None,
    ) -> dict[str, Any]:
        return {
            "case_id": fixture_dir.name,
            "metrics": {
                "contract": {"passed": True, "checks": {}},
                "authorships": {"names_f1": 1.0},
                "references": {"sample_arxiv_f1": 1.0, "sample_doi_f1": 1.0},
            },
            "predicted": {},
            "gold": {},
            "diagnostics": {},
        }

    store1 = BenchmarkTaskStore(
        max_workers=1,
        history_dir=hist,
        layer1_runner=_fake_layer1_runner,
    )
    monkeypatch.setattr(benchmark_api, "task_store", store1)
    run_id = store1.create_run(
        case_ids=["yolov1"],
        label="api-restore-label",
        benchmark_family="layer1",
        run_config={"model_profile": "env_default"},
    )
    deadline = time.time() + 10.0
    while time.time() < deadline:
        run = store1.get_run(run_id)
        if run and run.get("status") in {"completed", "failed", "cancelled"}:
            break
        time.sleep(0.05)
    assert store1.get_run(run_id)["status"] == "completed"

    store2 = BenchmarkTaskStore(
        max_workers=1,
        history_dir=hist,
        layer1_runner=_fake_layer1_runner,
    )
    monkeypatch.setattr(benchmark_api, "task_store", store2)

    client = _client()
    res = client.get("/v1/benchmark/runs")
    assert res.status_code == 200
    items = res.json().get("items") or []
    labels = [x.get("label") for x in items]
    assert "api-restore-label" in labels
