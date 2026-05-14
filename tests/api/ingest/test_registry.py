from __future__ import annotations

import threading
from types import SimpleNamespace
from typing import Any

import pytest

from science_graphrag.api.ingest.dto import IngestJobRecord
from science_graphrag.ingestion.jobs.registry import (
    IngestJobRegistry,
    get_ingest_job_registry,
    reset_ingest_job_registry_for_tests,
)


class _FakeSession:
    def __init__(self) -> None:
        self.added: list[Any] = []
        self.committed = False
        self.refreshed = False

    def __enter__(self) -> "_FakeSession":
        return self

    def __exit__(self, *_args: Any) -> None:
        return None

    def add(self, row: Any) -> None:
        self.added.append(row)

    def commit(self) -> None:
        self.committed = True

    def refresh(self, row: Any) -> None:
        self.refreshed = True
        if not getattr(row, "job_id", None):
            row.job_id = "generated-job-id"


class _SessionFactory:
    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    def __call__(self) -> _FakeSession:
        return self._session


def test_create_job_returns_view(monkeypatch: Any) -> None:
    fake_session = _FakeSession()
    registry = IngestJobRegistry.__new__(IngestJobRegistry)
    registry.lock = threading.Lock()
    registry._session_factory = _SessionFactory(fake_session)

    expected = IngestJobRecord(
        job_id="generated-job-id",
        workspace_id="ws-1",
        filename="paper.pdf",
        status="queued",
    )
    monkeypatch.setattr(registry, "_to_dataclass", lambda _row: expected)

    result = registry.create_job("ws-1", "paper.pdf")

    assert result.job_id == "generated-job-id"
    assert result.workspace_id == "ws-1"
    assert fake_session.committed is True
    assert fake_session.refreshed is True
    assert len(fake_session.added) == 1


def test_update_stage_status(monkeypatch: Any) -> None:
    registry = IngestJobRegistry.__new__(IngestJobRegistry)
    calls: list[dict[str, Any]] = []

    def _capture_update(job_id: str, **kwargs: Any) -> None:
        calls.append({"job_id": job_id, **kwargs})

    monkeypatch.setattr(registry, "update_job", _capture_update)

    registry.update_stage("job-1", status="running", message="started")

    assert calls == [{"job_id": "job-1", "status": "running", "message": "started"}]


def test_get_ingest_job_registry_rebinds_on_database_url_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from science_graphrag.ingestion.jobs import registry as reg_mod

    reset_ingest_job_registry_for_tests()
    disposed: list[str] = []

    class _FakeReg:
        def __init__(self, settings: SimpleNamespace) -> None:
            self._url = str(settings.database_url).strip()

        @property
        def resolved_database_url(self) -> str:
            return self._url

    monkeypatch.setattr(reg_mod, "IngestJobRegistry", _FakeReg)
    monkeypatch.setattr(
        reg_mod,
        "dispose_engine_for_database_url",
        lambda u: disposed.append(str(u).strip()),
    )

    s1 = SimpleNamespace(database_url="sqlite:///ingest_registry_one")
    s2 = SimpleNamespace(database_url="sqlite:///ingest_registry_two")
    r1 = get_ingest_job_registry(s1)
    r2 = get_ingest_job_registry(s1)
    assert r1 is r2
    r3 = get_ingest_job_registry(s2)
    assert r3 is not r1
    assert disposed == ["sqlite:///ingest_registry_one"]
    reset_ingest_job_registry_for_tests()
    assert disposed == [
        "sqlite:///ingest_registry_one",
        "sqlite:///ingest_registry_two",
    ]
