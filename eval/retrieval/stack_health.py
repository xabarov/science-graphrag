"""Infra health checks for retrieval / multihop benchmarks (BT2/BT3)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


def check_api_health(api_base_url: str, *, timeout: float = 5.0) -> tuple[bool, str]:
    """Return (ok, detail) after GET ``{api_base_url}/health``."""

    url = f"{api_base_url.rstrip('/')}/health"
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                return True, "ok"
            return False, f"http_status_{resp.status_code}"
    except OSError as exc:
        return False, str(exc)
    except httpx.HTTPError as exc:
        return False, str(exc)


def write_skip_artifact(
    repo_root: Path,
    *,
    stem: str,
    payload: dict[str, Any],
) -> Path:
    """Write ``eval/results/{stem}-<UTC-iso>.json`` (stable sort for tests optional)."""

    out_dir = repo_root / "eval" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"{stem}-{ts}.json"
    body = {"schema_version": 1, **payload}
    path.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
