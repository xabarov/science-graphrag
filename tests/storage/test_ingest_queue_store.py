"""Local ingest queue store."""

from __future__ import annotations

from pathlib import Path

from science_graphrag.storage.ingest_queue_store import LocalIngestQueueStore


def test_local_ingest_queue_put_get_delete(tmp_path: Path) -> None:
    store = LocalIngestQueueStore(tmp_path)
    key = store.put("job-1", "paper.pdf", b"hello")
    assert key.startswith("ingest-queue/")
    dest = tmp_path / "out.bin"
    store.get_to_path(key, dest)
    assert dest.read_bytes() == b"hello"
    store.delete(key)
    assert not (tmp_path / "_ingest_queue").joinpath(Path(key).name).exists()
