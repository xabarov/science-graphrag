#!/usr/bin/env python3
"""Pre-flight: load ``.env`` then validate Settings (LLM key, service URLs).

Mirrors the operator smoke for long-running jobs: ensures ``extraction_llm_api_key``
is non-empty after merge rules. Does not open network connections.

Usage::

    cd /path/to/science-graphrag
    .venv/bin/python scripts/live_check/config_preflight.py
    .venv/bin/python scripts/live_check/config_preflight.py --json --strict
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_LIVE_DIR = Path(__file__).resolve().parent


def _mask(s: str | None, keep: int = 4) -> str:
    """Shorten secrets/URIs for logs."""
    if not s:
        return ""
    t = str(s).strip()
    if len(t) <= keep * 2:
        return "***"
    return f"{t[:keep]}…{t[-keep:]}"


def main() -> int:
    """CLI entry: optional strict exit codes for operator gates."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        type=Path,
        default=_REPO_ROOT / ".env",
        help="Dotenv path (default: repo .env)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if extraction_llm_api_key is empty",
    )
    parser.add_argument("--json", action="store_true", help="Machine-readable stdout")
    args = parser.parse_args()

    if str(_LIVE_DIR) not in sys.path:
        sys.path.insert(0, str(_LIVE_DIR))
    from dotenv_util import (  # pylint: disable=import-outside-toplevel,import-error
        load_dotenv_or_warn,
    )

    env_path = args.env_file.expanduser()
    loaded = load_dotenv_or_warn(env_path)

    sys.path.insert(0, str(_REPO_ROOT))
    from science_graphrag.config import Settings  # pylint: disable=import-outside-toplevel

    s = Settings()
    key_ok = bool((s.extraction_llm_api_key or "").strip())
    row = {
        "env_file": str(env_path),
        "env_loaded": loaded,
        "extraction_llm_api_key_set": key_ok,
        "extraction_llm_base_url": s.extraction_llm_base_url,
        "extraction_llm_model": s.extraction_llm_model,
        "agent_runtime": s.agent_runtime,
        "neo4j_uri": _mask(s.neo4j_uri),
        "qdrant_url": str(s.qdrant_url or "")[:80],
    }
    if args.json:
        print(json.dumps(row, indent=2, ensure_ascii=False))
    else:
        print(f"extraction_llm_api_key_set: {key_ok}")
        print(f"extraction_llm_model: {s.extraction_llm_model}")
        print(f"extraction_llm_base_url: {s.extraction_llm_base_url}")

    issues: list[str] = []
    if not key_ok:
        issues.append("extraction_llm_api_key_missing")
    if issues:
        if not args.json:
            print("issues:", ", ".join(issues), file=sys.stderr)
        return 1
    if args.strict and not key_ok:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
