#!/usr/bin/env python3
"""Pre-flight Neo4j + Qdrant completeness audit for a benchmark chat workspace."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eval.chat_agent.workspace_audit import audit_workspace_readiness
from science_graphrag.api.deps import close_store_registry, init_store_registry
from science_graphrag.config import get_settings


def _load_manifest(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("manifest must be a JSON object")
    return raw


def _render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Chat-agent workspace readiness audit",
        "",
        f"- **Generated:** {summary.get('generated_at')}",
        f"- **Workspace:** `{summary.get('workspace_id')}`",
        f"- **Status:** **{summary.get('status')}**",
        "",
        "## Per-work checks",
        "",
        "| work_id | Neo4j | authors | CITES→ | chunks (all) | chunks (ws) | flags |",
        "|---------|-------|---------|--------|--------------|-------------|-------|",
    ]
    for row in summary.get("work_reports") or []:
        flags = ", ".join(row.get("flags") or []) or "—"
        lines.append(
            f"| `{row.get('work_id')}` | "
            f"{'yes' if row.get('neo4j_work_exists') else 'no'} | "
            f"{row.get('author_rows')} | "
            f"{row.get('outgoing_cites_count')} | "
            f"{row.get('qdrant_chunk_points_total')} | "
            f"{row.get('qdrant_chunk_points_workspace_scoped')} | "
            f"{flags} |",
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- **ready**: all works exist, have chunks, workspace-scoped chunk payloads present, graph cites present.",  # noqa: E501
            "- **degraded**: runnable for some roadmap cases but missing authors / cites / workspace_ids on chunks.",
            "- **blocked**: missing workspace, work nodes, or chunks — do not use as chat baseline.",
            "",
        ],
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="Path to baseline_workspace_manifest.json",
    )
    parser.add_argument(
        "--workspace-id",
        type=str,
        default="",
        help="Override workspace id from manifest",
    )
    parser.add_argument(
        "--out-json", type=Path, default=None, help="Write machine-readable summary"
    )
    parser.add_argument("--out-md", type=Path, default=None, help="Write human-readable summary")
    args = parser.parse_args()

    manifest = _load_manifest(args.manifest)
    ws_id = (args.workspace_id or manifest.get("workspace_id") or "").strip()
    if not ws_id:
        print("error: workspace_id missing", file=sys.stderr)
        return 2

    settings = get_settings()
    stores = init_store_registry(settings)
    try:
        body = audit_workspace_readiness(workspace_id=ws_id, stores=stores)
    finally:
        close_store_registry()

    summary: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "manifest_path": str(args.manifest),
        **body,
    }

    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text(_render_markdown(summary), encoding="utf-8")

    print(json.dumps({"status": summary["status"], "workspace_id": ws_id}, indent=2))
    return 0 if summary["status"] != "blocked" else 3


if __name__ == "__main__":
    raise SystemExit(main())
