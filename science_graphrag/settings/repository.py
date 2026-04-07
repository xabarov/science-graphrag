"""Persistence for non-secret runtime settings."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SettingsRepository:
    """Persist editable non-secret settings in a local JSON document."""

    def __init__(self, root_dir: Path) -> None:
        self._root_dir = root_dir

    @property
    def path(self) -> Path:
        return self._root_dir / "runtime_settings.json"

    def load(self) -> dict[str, Any]:
        path = self.path
        if not path.is_file():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(payload, dict):
            return {}
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        self._root_dir.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
