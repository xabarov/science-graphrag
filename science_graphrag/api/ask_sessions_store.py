"""File-backed Ask session persistence (server-side alternative to localStorage)."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_scope(scope: str) -> str:
    s = (scope or "").strip()
    if not s or len(s) > 256:
        raise ValueError("invalid_scope")
    if not re.match(r"^[A-Za-z0-9:_\-]+$", s):
        raise ValueError("invalid_scope_chars")
    return s


def _store_path(repo_root: Path, scope: str) -> Path:
    d = repo_root / "data" / "ask_sessions"
    d.mkdir(parents=True, exist_ok=True)
    safe = _sanitize_scope(scope).replace("/", "_")
    return d / f"{safe}.json"


@dataclass
class AskSessionsFileStore:
    """JSON document per scope: sessions[], active_session_id."""

    repo_root: Path
    _lock: Lock = field(default_factory=Lock, repr=False, compare=False)

    def load(self, scope: str) -> dict[str, Any]:
        path = _store_path(self.repo_root, scope)
        if not path.is_file():
            return {"scope": scope, "sessions": [], "active_session_id": None}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            return {"scope": scope, "sessions": [], "active_session_id": None}
        if not isinstance(data, dict):
            return {"scope": scope, "sessions": [], "active_session_id": None}
        data.setdefault("sessions", [])
        data.setdefault("active_session_id", None)
        data["scope"] = scope
        return data

    def save(self, scope: str, payload: dict[str, Any]) -> None:
        path = _store_path(self.repo_root, scope)
        with self._lock:
            path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    def list_sessions(self, scope: str) -> dict[str, Any]:
        return self.load(scope)

    def create_session(self, scope: str, title: str | None) -> dict[str, Any]:
        data = self.load(scope)
        sid = str(uuid.uuid4())
        row = {
            "id": sid,
            "title": (title or "Session").strip()[:200] or "Session",
            "updated_at": _now_iso(),
            "turns": [],
        }
        sessions = list(data.get("sessions") or [])
        sessions.append(row)
        data["sessions"] = sessions
        data["active_session_id"] = sid
        self.save(scope, data)
        return row

    def patch_session(
        self,
        scope: str,
        session_id: str,
        *,
        title: str | None = None,
        turns: list[dict[str, Any]] | None = None,
        make_active: bool = False,
    ) -> dict[str, Any] | None:
        data = self.load(scope)
        sessions: list[dict[str, Any]] = list(data.get("sessions") or [])
        found: dict[str, Any] | None = None
        for i, s in enumerate(sessions):
            if str(s.get("id")) == session_id:
                found = dict(s)
                if title is not None:
                    found["title"] = title.strip()[:200] or found.get("title", "Session")
                if turns is not None:
                    found["turns"] = list(turns)
                found["updated_at"] = _now_iso()
                sessions[i] = found
                break
        if found is None:
            return None
        data["sessions"] = sessions
        if make_active:
            data["active_session_id"] = session_id
        self.save(scope, data)
        return found

    def delete_session(self, scope: str, session_id: str) -> bool:
        data = self.load(scope)
        before = list(data.get("sessions") or [])
        sessions = [s for s in before if str(s.get("id")) != session_id]
        if len(sessions) == len(before):
            return False
        data["sessions"] = sessions
        if data.get("active_session_id") == session_id:
            data["active_session_id"] = sessions[-1]["id"] if sessions else None
        self.save(scope, data)
        return True


def default_ask_sessions_store() -> AskSessionsFileStore:
    repo_root = Path(__file__).resolve().parents[2]
    return AskSessionsFileStore(repo_root=repo_root)
