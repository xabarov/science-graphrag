"""Ask session file-backed API."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from science_graphrag.api import ask_sessions as ask_mod
from science_graphrag.api import main as api_main
from science_graphrag.api.ask_sessions_store import AskSessionsFileStore


def test_ask_sessions_roundtrip(tmp_path: Any, monkeypatch: Any) -> None:
    monkeypatch.setattr(ask_mod, "_store", AskSessionsFileStore(repo_root=tmp_path))
    client = TestClient(api_main.app)

    listed = client.get("/v1/ask-sessions", params={"scope": "standalone"})
    assert listed.status_code == 200
    assert listed.json()["sessions"] == []

    created = client.post("/v1/ask-sessions", json={"scope": "standalone", "title": "Alpha"})
    assert created.status_code == 200
    sid = created.json()["session"]["id"]

    patched = client.patch(
        f"/v1/ask-sessions/{sid}",
        params={"scope": "standalone"},
        json={"title": "Beta", "turns": [{"q": "hello"}], "active": True},
    )
    assert patched.status_code == 200
    assert patched.json()["session"]["title"] == "Beta"
    assert len(patched.json()["session"]["turns"]) == 1

    final = client.get("/v1/ask-sessions", params={"scope": "standalone"})
    assert final.status_code == 200
    assert final.json()["active_session_id"] == sid

    deleted = client.delete(f"/v1/ask-sessions/{sid}", params={"scope": "standalone"})
    assert deleted.status_code == 200
