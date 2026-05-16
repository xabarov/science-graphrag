"""Settings SPA section catalog contract."""

from __future__ import annotations

from science_graphrag.settings.snapshot_sections import build_settings_sections_catalog


def test_settings_sections_catalog_has_stable_ids_without_rollout_status() -> None:
    sections = build_settings_sections_catalog()
    ids = [row["id"] for row in sections]
    assert ids == [
        "general",
        "llm",
        "ingestion",
        "storage",
        "benchmark",
        "security",
        "diagnostics",
        "agent_tools",
    ]
    for row in sections:
        assert row["id"]
        assert row["label"]
        assert row["description"]
        assert "status" not in row
