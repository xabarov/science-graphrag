#!/usr/bin/env python3
"""Freeze rich OD workspace manifest + readiness snapshot (Task 1)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eval.chat_agent.od_cli_support import build_od_workspace_manifest_live
from eval.chat_agent.od_workspace_manifest import render_od_workspace_manifest_markdown
from science_graphrag.artifacts.diagnostic_object_sink import (
    default_local_diagnostics_dir,
    write_diagnostic_json,
)
from science_graphrag.config import get_settings


def _default_out_json() -> Path:
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return default_local_diagnostics_dir("od") / f"od-workspace-manifest-{ts}.json"


def main() -> int:
    """Entry point for ``python scripts/chat_agent_od_workspace_manifest.py``."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workspace-id",
        type=str,
        required=True,
        help="Neo4j Workspace.id (UUID for rich OD lane).",
    )
    parser.add_argument(
        "--lane",
        type=str,
        default="rich_od",
        help="Lane label stored in manifest JSON (default: rich_od).",
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        default=None,
        help=f"Write manifest JSON (default: {_default_out_json()!s}).",
    )
    parser.add_argument("--out-md", type=Path, default=None, help="Optional Markdown summary path.")
    args = parser.parse_args()

    out_json = args.out_json or _default_out_json()

    body = build_od_workspace_manifest_live(
        workspace_id=args.workspace_id.strip(),
        lane=args.lane.strip() or "rich_od",
    )

    summary: dict[str, Any] = {
        **body,
        "artifact_written_at": datetime.now(UTC).isoformat(),
    }

    settings = get_settings()
    written = write_diagnostic_json(
        out_json.name,
        summary,
        settings=settings,
        kind="od",
        local_path=out_json,
    )

    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text(render_od_workspace_manifest_markdown(summary), encoding="utf-8")

    wc = summary.get("work_count")
    print(
        json.dumps(
            {
                "written": written,
                "work_count": wc,
                "workspace_id": summary.get("workspace_id"),
            },
            indent=2,
        )
    )
    if wc != 31:
        print(
            f"warning: expected 31 works for canonical rich OD manifest; got {wc}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
