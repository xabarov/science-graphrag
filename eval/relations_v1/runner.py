"""Run relation-level benchmark: full ingest then score Neo4j :USES_METHOD / :EVALUATED_ON vs semantic gold."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Any

import typer
from neo4j import GraphDatabase, NotificationClassification

from eval.bench_common import (
    discover_layer2_case_dirs,
    run_single_case_json_outputs,
    run_suite_cli_flow,
)
from eval.layer2.metrics import score_semantic
from eval.layer2.spec import SemanticGoldSpec
from science_graphrag.config import Settings, get_settings
from science_graphrag.domain.semantic_models import (
    SemanticDatasetV1,
    SemanticExtractionV1,
    SemanticMethodV1,
)
from science_graphrag.ingestion.pipeline import ingest_document
from science_graphrag.storage.neo4j_store import Neo4jGraphStore


def _relations_eval_settings(base: Settings, case_id: str, temp_root: Path) -> Settings:
    return base.model_copy(
        update={
            "artifact_root": temp_root / "artifacts",
            "blob_root": temp_root / "blobs",
            "qdrant_collection": f"relations-eval-{case_id}-{uuid.uuid4().hex[:8]}",
            "reuse_cached_markdown": False,
        },
    )


def _resolve_article_path(case_dir: Path, gold: SemanticGoldSpec) -> Path:
    if gold.article_path:
        return (case_dir / gold.article_path).resolve()
    return (case_dir / "article.md").resolve()


def _query_semantic_projection(
    settings: Settings, work_id: str, document_id: str
) -> SemanticExtractionV1:
    methods: list[SemanticMethodV1] = []
    datasets: list[SemanticDatasetV1] = []
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
        notifications_disabled_classifications=[NotificationClassification.UNRECOGNIZED],
    )
    try:
        with driver.session() as session:
            mrows = session.run(
                """
                MATCH (:Work {id: $wid})-[:USES_METHOD]->(m:Method)
                RETURN DISTINCT coalesce(m.name, '') AS name, coalesce(m.aliases, []) AS aliases
                """,
                wid=work_id,
            )
            for rec in mrows:
                name = str(rec["name"] or "").strip()
                if not name:
                    continue
                raw_aliases = rec["aliases"] or []
                aliases: list[str] = []
                if isinstance(raw_aliases, list):
                    aliases = [str(a).strip() for a in raw_aliases if str(a).strip()]
                methods.append(
                    SemanticMethodV1(name=name, aliases=aliases, confidence=1.0),
                )
            drows = session.run(
                """
                MATCH (:Work {id: $wid})-[:EVALUATED_ON]->(d:Dataset)
                RETURN DISTINCT coalesce(d.name, '') AS name, coalesce(d.aliases, []) AS aliases
                """,
                wid=work_id,
            )
            for rec in drows:
                name = str(rec["name"] or "").strip()
                if not name:
                    continue
                raw_aliases = rec["aliases"] or []
                aliases = []
                if isinstance(raw_aliases, list):
                    aliases = [str(a).strip() for a in raw_aliases if str(a).strip()]
                datasets.append(
                    SemanticDatasetV1(name=name, aliases=aliases, confidence=1.0),
                )
    finally:
        driver.close()
    return SemanticExtractionV1(
        document_id=document_id,
        methods=methods,
        datasets=datasets,
        relations=[],
    )


def run_case(
    fixture_dir: Path | str,
    *,
    settings: Settings | None = None,
    wipe_neo4j: bool = True,
) -> dict[str, Any]:
    """Ingest article for a layer-2 semantic fixture, then compare Neo4j semantic edges to gold."""

    root = Path(fixture_dir)
    gold = SemanticGoldSpec.load(root / "semantic_gold.json")
    article_path = _resolve_article_path(root, gold)
    if not article_path.is_file():
        raise FileNotFoundError(f"article not found: {article_path}")
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

    with tempfile.TemporaryDirectory(prefix=f"relations-eval-{gold.case_id}-") as tmpdir:
        temp_root = Path(tmpdir)
        case_copy = temp_root / f"{gold.case_id}.md"
        case_copy.write_text(article_path.read_text(encoding="utf-8"), encoding="utf-8")
        local_settings = _relations_eval_settings(settings, gold.case_id, temp_root)
        document_id, work_id = ingest_document(case_copy, settings=local_settings, session=None)

    pred = _query_semantic_projection(settings, work_id, document_id)
    metrics = score_semantic(
        pred,
        gold,
        extraction_llm_enabled=bool(settings.extraction_llm_enabled),
        confidence_threshold=float(settings.semantic_graph_confidence_threshold),
    )
    return {
        "case_id": gold.case_id,
        "fixture_dir": str(root.resolve()),
        "article_path": str(article_path),
        "document_id": document_id,
        "work_id": work_id,
        "metrics": metrics.to_json_dict(),
        "predicted_from_neo4j": pred.model_dump(mode="json", by_alias=True),
        "gold": gold.model_dump_for_report(),
    }


def _summarize(report: dict[str, Any]) -> str:
    m = report["metrics"]
    lines = [
        f"# Relations benchmark (Neo4j): {report['case_id']}",
        "",
        f"- work_id: {report['work_id']}",
        f"- article: {report.get('article_path')}",
        "",
        "## Metrics (same scorer as layer-2 JSON, predictions read from Neo4j)",
        f"- passed: {m.get('passed')}",
        f"- notes: {m.get('notes')}",
        f"- precision_methods: {m.get('precision_methods')}",
        f"- recall_methods: {m.get('recall_methods_num')}/{m.get('recall_methods_denom')}",
        f"- precision_datasets: {m.get('precision_datasets')}",
        f"- recall_datasets: {m.get('recall_datasets_num')}/{m.get('recall_datasets_denom')}",
        "",
    ]
    return "\n".join(lines)


def _cli(
    path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Layer-2 case directory, or suite root with --suite",
    ),
    suite: bool = typer.Option(
        False,
        "--suite",
        "-s",
        help="Run every layer-2 benchmark case under path",
    ),
    json_out: Path | None = typer.Option(None, "--json-out", help="Write JSON suite/case report"),
    md_out: Path | None = typer.Option(None, "--md-out", help="Write Markdown summary"),
    no_wipe: bool = typer.Option(False, "--no-wipe", help="Do not wipe Neo4j before each case"),
    tier: str | None = typer.Option(
        None,
        "--tier",
        help='Filter suite via layer2/case_tiers.json (e.g. "relations_pilot", "nightly_semantic")',
    ),
) -> None:
    settings = get_settings()
    wipe = not no_wipe

    def _passed(rep: dict[str, Any]) -> bool:
        return bool(rep.get("metrics", {}).get("passed", True))

    if suite:
        cases = discover_layer2_case_dirs(path, tier=tier)
        if not cases:
            typer.echo(f"No layer-2 benchmarks found under {path}", err=True)
            raise typer.Exit(code=1)
        payload = run_suite_cli_flow(
            title="Relations (Neo4j semantic materialization) benchmark suite",
            cases=cases,
            settings=settings,
            run_one=lambda c: run_case(c, settings=settings, wipe_neo4j=wipe),
            summarize=_summarize,
            json_out=json_out,
            md_out=md_out,
            summary_from_reports=lambda reports: {
                "all_passed": all(_passed(r) for r in reports),
                "relations_neo4j_eval": True,
            },
        )
        if not bool(payload.get("summary", {}).get("all_passed", True)):
            raise typer.Exit(code=1)
        return

    report = run_case(path, settings=settings, wipe_neo4j=wipe)
    run_single_case_json_outputs(
        report=report,
        settings=settings,
        summarize=_summarize,
        json_out=json_out,
        md_out=md_out,
    )
    if not _passed(report):
        raise typer.Exit(code=1)


def main() -> None:
    typer.run(_cli)


if __name__ == "__main__":
    main()
