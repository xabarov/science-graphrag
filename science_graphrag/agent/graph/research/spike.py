"""Y5: LangGraph research spike CLI placeholder (same JSON envelope as smolagents spike target)."""

from __future__ import annotations

import json
import sys
from typing import Any

import typer

app = typer.Typer(add_completion=False, help="Y5 LangGraph research spike (stub).")


@app.command("suite")
def suite_stub() -> None:
    """Emit a minimal JSON document describing the planned LangGraph suite contract."""
    payload: dict[str, Any] = {
        "schema": "refs_langgraph_spike_stub_v1",
        "note": "Install optional [agent] and implement graph nodes; see docs/analysis/langgraph-migration-plan-2026-04-25.md",
        "rows": [],
    }
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
