from __future__ import annotations

import threading
from typing import Any

from science_graphrag.api.ingest.dto import IngestJobRecord
from science_graphrag.api.ingest.registry import IngestJobRegistry


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

    monkeypatch.setattr(registry, "_update", _capture_update)

    registry.update_stage("job-1", status="running", message="started")

    assert calls == [{"job_id": "job-1", "status": "running", "message": "started"}]
