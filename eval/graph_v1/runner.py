"""Run graph-level benchmark cases against full ingest + Neo4j."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Any

import typer
from neo4j import GraphDatabase, NotificationClassification

from eval.bench_common import (
    discover_layer1_case_dirs,
    run_single_case_json_outputs,
    run_suite_cli_flow,
)
from eval.graph_v1.metrics import GraphSnapshot, score_graph_snapshot
from eval.layer1.spec import Layer1GoldSpec
from science_graphrag.config import Settings, get_settings
from science_graphrag.ingestion.pipeline import ingest_document
from science_graphrag.storage.neo4j_store import Neo4jGraphStore


def _graph_eval_settings(base: Settings, case_id: str, temp_root: Path) -> Settings:
    return base.model_copy(
        update={
            "artifact_root": temp_root / "artifacts",
            "blob_root": temp_root / "blobs",
            "qdrant_collection": f"graph-eval-{case_id}-{uuid.uuid4().hex[:8]}",
            "reuse_cached_markdown": False,
        }
    )


def _query_graph_snapshot(settings: Settings, work_id: str) -> GraphSnapshot:
    """Read compact Neo4j snapshot for one work after ingest."""

    work_row = None
    auth_count = None
    inst_count = None
    cites_row = None
    dup_row = None
    rel_row = None
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
        notifications_disabled_classifications=[NotificationClassification.UNRECOGNIZED],
    )
    try:
        with driver.session() as session:
            work_row = session.run(
                """
                MATCH (w:Work {id: $work_id})
                RETURN w.title AS title
                """,
                work_id=work_id,
            ).single()
            auth_count = session.run(
                """
                MATCH (:Work {id: $work_id})-[:HAS_AUTHORSHIP]->(x:Authorship)
                RETURN count(DISTINCT x) AS n
                """,
                work_id=work_id,
            ).single()
            inst_count = session.run(
                """
                MATCH (:Work {id: $work_id})-[:HAS_AUTHORSHIP]->(:Authorship)
                      -[:AFFILIATED_WITH]->(i:Institution)
                RETURN count(DISTINCT i) AS n
                """,
                work_id=work_id,
            ).single()
            cites_row = session.run(
                """
                MATCH (:Work {id: $work_id})-[:CITES]->(c:Work)
                RETURN count(DISTINCT c) AS n, collect(DISTINCT c.arxiv_id) AS arxiv_ids
                """,
                work_id=work_id,
            ).single()
            dup_row = session.run("""
                MATCH (w:Work)
                WHERE w.fingerprint IS NOT NULL
                WITH w.fingerprint AS fp, count(*) AS n
                WHERE n > 1
                RETURN count(fp) AS duplicate_fingerprints
                """).single()
            rel_row = session.run(
                """
                MATCH (w:Work {id: $work_id})-[r:RELATED_VERSION_OF]-()
                RETURN count(r) AS n
                """,
                work_id=work_id,
            ).single()
    finally:
        driver.close()

    rel_n = int(rel_row["n"] if rel_row else 0)

    audit = Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    try:
        viol_n = len(audit.find_work_dedup_violations())
    finally:
        audit.close()

    return GraphSnapshot(
        work_id=work_id,
        work_title=work_row["title"] if work_row else None,
        authorship_count=auth_count["n"] if auth_count else 0,
        institution_count=inst_count["n"] if inst_count else 0,
        cites_count=cites_row["n"] if cites_row else 0,
        cited_arxiv_ids=sorted(
            [value for value in (cites_row["arxiv_ids"] if cites_row else []) if value]
        ),
        duplicate_work_fingerprints=(dup_row["duplicate_fingerprints"] if dup_row else 0),
        related_version_edge_count=rel_n,
        work_dedup_violation_count=viol_n,
    )


def run_case(
    fixture_dir: Path | str,
    *,
    settings: Settings | None = None,
    wipe_neo4j: bool = True,
) -> dict[str, Any]:
    """Run full ingest on fixture markdown, then score Neo4j graph snapshot."""

    root = Path(fixture_dir)
    text = (root / "article.md").read_text(encoding="utf-8")
    gold = Layer1GoldSpec.load(root / "gold.json")
    settings = settings or get_settings()

    if wipe_neo4j:
        neo = Neo4jGraphStore(
            settings.neo4j_uri,
            settings.neo4j_user,
            settings.neo4j_password,
        )
        try:
            neo.wipe_all()
        finally:
            neo.close()

    with tempfile.TemporaryDirectory(prefix=f"graph-eval-{gold.case_id}-") as tmpdir:
        temp_root = Path(tmpdir)
        case_path = temp_root / f"{gold.case_id}.md"
        case_path.write_text(text, encoding="utf-8")
        local_settings = _graph_eval_settings(settings, gold.case_id, temp_root)
        document_id, work_id = ingest_document(case_path, settings=local_settings, session=None)

    snapshot = _query_graph_snapshot(settings, work_id)
    metrics = score_graph_snapshot(snapshot, gold)
    return {
        "case_id": gold.case_id,
        "fixture_dir": str(root.resolve()),
        "document_id": document_id,
        "work_id": work_id,
        "metrics": metrics,
        "gold": gold.model_dump_for_report(),
    }


def _summarize(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    snapshot = metrics["snapshot"]
    lines = [
        f"# Graph-level benchmark: {report['case_id']}",
        "",
        f"- document_id: {report['document_id']}",
        f"- work_id: {report['work_id']}",
        "",
        "## Snapshot",
        f"- work_title: {snapshot.get('work_title')}",
        f"- authorship_count: {snapshot.get('authorship_count')}",
        f"- institution_count: {snapshot.get('institution_count')}",
        f"- cites_count: {snapshot.get('cites_count')}",
        f"- duplicate_work_fingerprints: {snapshot.get('duplicate_work_fingerprints')}",
        f"- related_version_edge_count: {snapshot.get('related_version_edge_count')}",
        f"- work_dedup_violation_count: {snapshot.get('work_dedup_violation_count')}",
        f"- cited_arxiv_ids: {snapshot.get('cited_arxiv_ids')}",
        "",
    ]
    if metrics.get("has_expectations"):
        lines.extend(
            [
                "## Checks",
                f"- cites_range_ok: {metrics.get('cites_range_ok')}",
                f"- authorships_range_ok: {metrics.get('authorships_range_ok')}",
                f"- institutions_range_ok: {metrics.get('institutions_range_ok')}",
                f"- cited_arxiv_precision: {metrics.get('cited_arxiv_precision')}",
                f"- cited_arxiv_recall: {metrics.get('cited_arxiv_recall')}",
                f"- cited_arxiv_f1: {metrics.get('cited_arxiv_f1')}",
                (
                    "- duplicate_work_fingerprints_ok: "
                    f"{metrics.get('duplicate_work_fingerprints_ok')}"
                ),
                f"- work_dedup_violations_ok: {metrics.get('work_dedup_violations_ok')}",
                f"- related_version_edges_ok: {metrics.get('related_version_edges_ok')}",
            ]
        )
    return "\n".join(lines)


def _cli(
    path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Case directory, or suite root with --suite",
    ),
    suite: bool = typer.Option(
        False,
        "--suite",
        "-s",
        help="Run every benchmark case under path (one subdir per case)",
    ),
    json_out: Path | None = typer.Option(None, "--json-out", help="Write JSON report"),
    md_out: Path | None = typer.Option(None, "--md-out", help="Write Markdown summary"),
    no_wipe: bool = typer.Option(False, "--no-wipe", help="Do not wipe Neo4j before run"),
    tier: str | None = typer.Option(
        None,
        "--tier",
        help='Filter suite to tier from case_tiers.json (e.g. "merge_safe", "nightly_heavy")',
    ),
) -> None:
    settings = get_settings()
    wipe = not no_wipe
    if suite:
        cases = discover_layer1_case_dirs(path, tier=tier)
        if not cases:
            typer.echo(f"No layer-1 benchmarks found under {path}", err=True)
            raise typer.Exit(code=1)
        run_suite_cli_flow(
            title="Graph-level benchmark suite",
            cases=cases,
            settings=settings,
            run_one=lambda c: run_case(c, settings=settings, wipe_neo4j=wipe),
            summarize=_summarize,
            json_out=json_out,
            md_out=md_out,
        )
        return

    report = run_case(path, settings=settings, wipe_neo4j=wipe)
    run_single_case_json_outputs(
        report=report,
        settings=settings,
        summarize=_summarize,
        json_out=json_out,
        md_out=md_out,
    )


def main() -> None:
    """CLI entrypoint for graph-level benchmark."""

    typer.run(_cli)


if __name__ == "__main__":
    main()
