#!/usr/bin/env python3
"""Task 4: audit Qdrant claim vectors for the rich OD workspace."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from eval.chat_agent.od_claim_vectors_audit import (
    build_od_claim_vectors_audit,
    render_od_claim_vectors_audit_markdown,
)
from eval.chat_agent.od_claims_backfill import load_json_object, read_jsonl_rows
from eval.chat_agent.od_cli_support import build_od_workspace_manifest_live
from science_graphrag.api.deps import close_store_registry, init_store_registry
from science_graphrag.artifacts.diagnostic_object_sink import (
    default_local_diagnostics_dir,
    write_diagnostic_json,
)
from science_graphrag.config import get_settings


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help=(
            "Optional frozen od-workspace-manifest JSON: used to read workspace_id when "
            "--workspace-id is omitted. Per-work counts in the audit always come from a "
            "live manifest built via store registry (current Neo4j/Qdrant/Postgres), not "
            "from this file's frozen counts."
        ),
    )
    parser.add_argument(
        "--workspace-id",
        type=str,
        default="",
        help="Live fallback: build current manifest for this workspace.",
    )
    parser.add_argument(
        "--task3-progress",
        type=Path,
        default=None,
        help="Optional od-claims-backfill JSONL to annotate restored works.",
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        default=default_local_diagnostics_dir("od") / "od-claim-vectors-audit-latest.json",
        help="Machine-readable audit path.",
    )
    parser.add_argument(
        "--out-md",
        type=Path,
        default=default_local_diagnostics_dir("od") / "od-claim-vectors-audit-latest.md",
        help="Human-readable audit path.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    if not args.manifest and not args.workspace_id.strip():
        raise SystemExit("error: pass --manifest or --workspace-id")

    if args.manifest:
        manifest = load_json_object(args.manifest)
        workspace_id = str(manifest.get("workspace_id") or "").strip()
    else:
        workspace_id = args.workspace_id.strip()
    live_manifest = build_od_workspace_manifest_live(workspace_id=workspace_id)
    task3_progress_rows = read_jsonl_rows(args.task3_progress)

    settings = get_settings()
    stores = init_store_registry(settings)
    try:
        audit = build_od_claim_vectors_audit(
            live_manifest,
            qdrant_claims_store=stores.qdrant_claims,
            task3_progress_rows=task3_progress_rows,
        )
    finally:
        close_store_registry()

    written_json = write_diagnostic_json(
        args.out_json.name,
        audit,
        settings=settings,
        kind="od",
        local_path=args.out_json,
    )
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(render_od_claim_vectors_audit_markdown(audit), encoding="utf-8")
    print(
        json.dumps(
            {
                "written_json": written_json,
                "written_md": str(args.out_md.resolve()),
                "summary": audit.get("summary"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
