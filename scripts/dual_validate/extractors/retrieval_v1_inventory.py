"""Corpus inventory loading for ``retrieval_v1`` extractors (CATALOG + workspaces)."""

from __future__ import annotations

import functools
import re
from pathlib import Path

CATALOG_PATH = Path("tests/fixtures/corpus/CATALOG.md")
WORKSPACES_PATH = Path("tests/fixtures/benchmarks/retrieval/workspace_scoped_live/_workspaces.json")

_TABLE_ROW = re.compile(r"^\|\s*`([a-z0-9_]+)`\s*\|\s*(.*?)\s*\|\s*([0-9n/a]+)\s*\|")


@functools.lru_cache(maxsize=1)
def load_inventory() -> dict[str, dict[str, str]]:
    """Parse CATALOG.md inventory table → ``{corpus_work_id: {title, year}}``."""

    inv: dict[str, dict[str, str]] = {}
    text = CATALOG_PATH.read_text(encoding="utf-8")
    for line in text.splitlines():
        m = _TABLE_ROW.match(line)
        if not m:
            continue
        wid, title, year = m.group(1), m.group(2), m.group(3)
        inv[wid] = {"title": title.strip(), "year": year.strip()}
    return inv


__all__ = ["CATALOG_PATH", "WORKSPACES_PATH", "load_inventory"]
