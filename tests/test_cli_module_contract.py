from __future__ import annotations

from typer.testing import CliRunner

from science_graphrag.cli.main import app

runner = CliRunner()


def test_cli_root_help_includes_split_command_groups() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in (
        "ingest",
        "ingest-corpus",
        "ingest-resume",
        "work-dedup-report",
        "neo4j-wipe",
        "qdrant-recreate-embedding-collections",
        "config-check",
    ):
        assert command in result.stdout


def test_ingest_resume_help_keeps_stages_option() -> None:
    result = runner.invoke(app, ["ingest-resume", "--help"])
    assert result.exit_code == 0
    assert "--stages" in result.stdout
    assert "embed, claims, references" in result.stdout


def test_ingest_help_keeps_no_cache_option() -> None:
    result = runner.invoke(app, ["ingest", "--help"])
    assert result.exit_code == 0
    assert "--no-cache" in result.stdout


def test_work_dedup_report_help_keeps_fail_on_clusters_option() -> None:
    result = runner.invoke(app, ["work-dedup-report", "--help"])
    assert result.exit_code == 0
    assert "--fail-on-clusters" in result.stdout
