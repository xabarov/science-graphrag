"""Secret storage for runtime settings."""

from __future__ import annotations

import json
from pathlib import Path


class SecretStore:
    """Simple local secret document for server-managed secrets."""

    def __init__(self, root_dir: Path) -> None:
        self._root_dir = root_dir

    @property
    def path(self) -> Path:
        return self._root_dir / "runtime_secrets.json"

    def _load_all(self) -> dict[str, str]:
        path = self.path
        if not path.is_file():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(payload, dict):
            return {}
        return {str(k): str(v) for k, v in payload.items() if isinstance(v, str)}

    def _save_all(self, payload: dict[str, str]) -> None:
        self._root_dir.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def get_secret(self, name: str) -> str | None:
        return self._load_all().get(name)

    def set_secret(self, name: str, value: str) -> None:
        payload = self._load_all()
        payload[name] = value
        self._save_all(payload)

    def delete_secret(self, name: str) -> None:
        payload = self._load_all()
        if name in payload:
            payload.pop(name, None)
            self._save_all(payload)
