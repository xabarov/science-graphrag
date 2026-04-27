#!/usr/bin/env python3
"""Root-cause audit for works missing Neo4j claims (Task 2)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eval.chat_agent.od_claims_gap_audit import (
    build_od_claims_gap_audit,
    render_od_claims_gap_audit_markdown,
)
from eval.chat_agent.od_cli_support import build_od_workspace_manifest_live
from science_graphrag.artifacts.diagnostic_object_sink import (
    default_local_diagnostics_dir,
    write_diagnostic_json,
)
from science_graphrag.config import get_settings


def _default_out_json() -> Path:
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return default_local_diagnostics_dir("od") / f"od-claims-gap-audit-{ts}.json"


def _load_manifest(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("manifest must be a JSON object")
    return raw


def main() -> int:
    """Entry point for ``python scripts/chat_agent_od_claims_gap_audit.py``."""
    parser = argparse.ArgumentParser(description=__doc__)
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument(
        "--manifest",
        type=Path,
        help="Path to frozen od-workspace-manifest-*.json from Task 1.",
    )
    src.add_argument(
        "--workspace-id",
        type=str,
        help="Build manifest from live stores, then run gap audit (no manifest file write).",
    )
    parser.add_argument(
        "--ingest-progress",
        type=Path,
        action="append",
        default=[],
        help="Optional ingest-progress JSONL (repeatable); last row per path/doc_id wins.",
    )
    parser.add_argument(
        "--lane",
        type=str,
        default="rich_od",
        help="Lane label when using --workspace-id (default: rich_od).",
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        default=None,
        help=f"Write audit JSON (default: {_default_out_json()!s}).",
    )
    parser.add_argument("--out-md", type=Path, default=None, help="Optional Markdown summary path.")
    args = parser.parse_args()

    out_json = args.out_json or _default_out_json()
    progress_paths = [p for p in (args.ingest_progress or []) if p]

    if args.manifest:
        manifest = _load_manifest(args.manifest)
    else:
        manifest = build_od_workspace_manifest_live(
            workspace_id=args.workspace_id.strip(),
            lane=args.lane.strip() or "rich_od",
        )

    audit = build_od_claims_gap_audit(manifest, ingest_progress_paths=progress_paths)
    audit["source_manifest_path"] = str(args.manifest) if args.manifest else None

    settings = get_settings()
    written = write_diagnostic_json(
        out_json.name,
        audit,
        settings=settings,
        kind="od",
        local_path=out_json,
    )

    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text(render_od_claims_gap_audit_markdown(audit), encoding="utf-8")

    summ = audit.get("summary") or {}
    print(json.dumps({"written": written, "summary": summ}, indent=2))

    missing = int(
        summ.get("work_count_missing_claims") or summ.get("work_count_missing_neo4j_claims") or 0
    )
    if missing != 28:
        msg = (
            "warning: expected 28 works missing Neo4j claims for canonical OD snapshot; "
            f"got {missing}"
        )
        print(msg, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
