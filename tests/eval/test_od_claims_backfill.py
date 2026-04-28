"""Unit tests for OD claims backfill helpers."""

from __future__ import annotations

import json
from types import SimpleNamespace

from eval.chat_agent.od_claims_backfill import (
    load_live_claims_as_drafts,
    resolve_workspace_id_for_row,
    resume_success_work_ids,
    select_task3_rows,
    select_task4_work_ids,
)


def test_select_task3_rows_gates_unknown_by_default() -> None:
    gap_audit = {
        "work_reports": [
            {"work_id": "w-ok", "claims_gap_classification": "claims_stage_not_run"},
            {"work_id": "w-unknown", "claims_gap_classification": "unknown"},
            {"work_id": "w-embed", "claims_gap_classification": "claims_embed_missing"},
        ]
    }
    rows = select_task3_rows(
        manifest=None,
        gap_audit=gap_audit,
        explicit_work_ids=None,
        allow_unknown=False,
    )
    assert [row["work_id"] for row in rows] == ["w-ok"]


def test_select_task3_rows_allows_unknown_with_flag() -> None:
    gap_audit = {
        "work_reports": [
            {"work_id": "w-ok", "claims_gap_classification": "claims_write_failed"},
            {"work_id": "w-unknown", "claims_gap_classification": "unknown"},
        ]
    }
    rows = select_task3_rows(
        manifest=None,
        gap_audit=gap_audit,
        explicit_work_ids=None,
        allow_unknown=True,
    )
    assert [row["work_id"] for row in rows] == ["w-ok", "w-unknown"]


def test_resume_success_work_ids_only_reads_ok_rows(tmp_path) -> None:
    progress = tmp_path / "progress.jsonl"
    progress.write_text(
        "\n".join(
            [
                json.dumps({"work_id": "w1", "status": "ok"}),
                json.dumps({"work_id": "w2", "status": "error"}),
                json.dumps({"work_id": "w3", "status": "skipped"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    assert resume_success_work_ids(progress) == {"w1"}


def test_load_live_claims_as_drafts_rehydrates_evidence(monkeypatch) -> None:
    monkeypatch.setattr(
        "eval.chat_agent.od_claims_backfill.list_work_claims",
        lambda *_args, **_kwargs: [
            {
                "claim_id": "claim-1",
                "normalized_text": "Detector improves AP.",
                "claim_type": "performance",
                "polarity": "positive",
                "confidence": 0.75,
                "evidence": [
                    {
                        "chunk_fingerprint": "cfp-1",
                        "quote": "AP improved by 2 points.",
                        "section_path": "Results",
                    }
                ],
            }
        ],
    )
    drafts = load_live_claims_as_drafts(SimpleNamespace(), work_id="w1")
    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.claim_id == "claim-1"
    assert draft.normalized_text == "Detector improves AP."
    assert draft.evidence[0].chunk_fingerprint == "cfp-1"
    assert draft.evidence[0].section_path == "Results"


def test_select_task4_work_ids_unions_gap_audit_and_task3_progress() -> None:
    manifest = {
        "work_reports": [
            {"work_id": "w1", "neo4j_claim_count": 2, "qdrant_claim_vector_count": 0},
            {"work_id": "w2", "neo4j_claim_count": 0, "qdrant_claim_vector_count": 0},
        ]
    }
    gap_audit = {
        "work_reports": [{"work_id": "w-gap", "claims_gap_classification": "claims_embed_missing"}]
    }
    progress_rows = [
        {"work_id": "w-progress", "status": "ok"},
        {"work_id": "w-failed", "status": "error"},
    ]
    assert select_task4_work_ids(
        manifest=manifest,
        gap_audit=gap_audit,
        task3_progress_rows=progress_rows,
        explicit_work_ids=None,
    ) == ["w-gap", "w-progress"]


def test_resolve_workspace_id_prefers_cli_then_row_then_manifests() -> None:
    row = {"work_id": "w1", "workspace_id": "from-row"}
    manifest = {"workspace_id": "from-manifest"}
    gap_audit = {"workspace_id": "from-gap"}
    assert (
        resolve_workspace_id_for_row(
            row=row,
            manifest=manifest,
            gap_audit=gap_audit,
            cli_workspace_id="cli-ws",
        )
        == "cli-ws"
    )
    assert (
        resolve_workspace_id_for_row(
            row={"work_id": "w1"},
            manifest=manifest,
            gap_audit=gap_audit,
            cli_workspace_id="",
        )
        == "from-manifest"
    )
    assert (
        resolve_workspace_id_for_row(
            row=row,
            manifest=manifest,
            gap_audit=gap_audit,
            cli_workspace_id="",
        )
        == "from-row"
    )
    assert (
        resolve_workspace_id_for_row(
            row={"work_id": "w1"},
            manifest={},
            gap_audit=gap_audit,
            cli_workspace_id="",
        )
        == "from-gap"
    )
    assert (
        resolve_workspace_id_for_row(
            row={"work_id": "w1"},
            manifest={},
            gap_audit={},
            cli_workspace_id="",
        )
        is None
    )
