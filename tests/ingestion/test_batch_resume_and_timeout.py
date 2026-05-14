from __future__ import annotations

import time
from pathlib import Path
from types import SimpleNamespace

from science_graphrag.ingestion import _pipeline_impl as pipeline_impl
from science_graphrag.ingestion import pipeline_cli_entrypoints as cli_entry


class _DummyTx:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _DummySession:
    def begin(self):
        return _DummyTx()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _DummyFactory:
    def __call__(self):
        return _DummySession()


class _DummyNeo:
    def __init__(self, *_args, **_kwargs):
        return

    def find_work_dedup_violations(self):
        return []

    def close(self):
        return


def _stub_common(monkeypatch):
    monkeypatch.setattr(cli_entry, "init_tracer_provider", lambda: None)
    monkeypatch.setattr(
        cli_entry,
        "get_settings",
        lambda: SimpleNamespace(
            database_url="postgresql+psycopg://unused",
            neo4j_uri="bolt://unused",
            neo4j_user="unused",
            neo4j_password="unused",
        ),
    )
    monkeypatch.setattr(cli_entry, "get_engine", lambda _url: object())
    monkeypatch.setattr(cli_entry, "init_db", lambda _engine: None)
    monkeypatch.setattr(cli_entry, "session_factory", lambda _engine: _DummyFactory())
    monkeypatch.setattr(cli_entry, "Neo4jGraphStore", _DummyNeo)


def test_batch_timeout_marks_file_and_continues(monkeypatch, tmp_path: Path) -> None:
    _stub_common(monkeypatch)
    slow = tmp_path / "slow.md"
    fast = tmp_path / "fast.md"
    slow.write_text("slow", encoding="utf-8")
    fast.write_text("fast", encoding="utf-8")
    monkeypatch.setattr(cli_entry, "discover_corpus_files", lambda _dir: [slow, fast])

    def _ingest(path: Path, **_kwargs):
        if path == slow:
            time.sleep(2.0)
            return "doc-slow", "work-slow"
        return "doc-fast", "work-fast"

    monkeypatch.setattr(pipeline_impl, "ingest_document", _ingest)

    progress_file = tmp_path / "progress.jsonl"
    rows = cli_entry.run_ingest_batch_cli(
        tmp_path,
        continue_on_error=True,
        per_file_timeout_s=1,
        progress_file=progress_file,
    )

    assert len(rows) == 2
    assert rows[0]["status"] == "timeout"
    assert rows[1]["status"] == "ok"
    text = progress_file.read_text(encoding="utf-8")
    assert '"status": "timeout"' in text
    assert '"status": "ok"' in text


def test_batch_resume_skips_ok_files(monkeypatch, tmp_path: Path) -> None:
    _stub_common(monkeypatch)
    first = tmp_path / "one.md"
    second = tmp_path / "two.md"
    first.write_text("one", encoding="utf-8")
    second.write_text("two", encoding="utf-8")
    monkeypatch.setattr(cli_entry, "discover_corpus_files", lambda _dir: [first, second])

    progress_file = tmp_path / "progress.jsonl"
    progress_file.write_text(
        "\n".join(
            [
                '{"path": "%s", "status": "ok"}' % str(first.resolve()),
                '{"path": "%s", "status": "fail"}' % str(second.resolve()),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    calls = []

    def _ingest(path: Path, **_kwargs):
        calls.append(path)
        return "doc-two", "work-two"

    monkeypatch.setattr(pipeline_impl, "ingest_document", _ingest)

    rows = cli_entry.run_ingest_batch_cli(
        tmp_path,
        continue_on_error=True,
        resume=True,
        progress_file=progress_file,
    )

    assert [p.name for p in calls] == ["two.md"]
    assert rows[0]["status"] == "skip"
    assert rows[1]["status"] == "ok"
