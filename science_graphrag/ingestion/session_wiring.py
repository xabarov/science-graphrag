"""Session and engine wiring helpers for ingest orchestration."""

from __future__ import annotations

from sqlalchemy.orm import Session

from science_graphrag.config import Settings
from science_graphrag.storage.db import get_engine, init_db
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.utils.project_logging import get_logger

logger = get_logger("ingestion.session_wiring")


def sql_commit_if_session(session: Session | None) -> None:
    """Commit SQL work when an explicit session is present."""
    if session is not None:
        session.commit()


def build_ingest_engine(settings: Settings):
    """Create and initialize SQL engine for ingest commands."""
    engine = get_engine(settings.database_url)
    init_db(engine)
    return engine


def run_dedup_audit(settings: Settings) -> None:
    """Log post-batch Neo4j dedup audit summary."""
    neo = Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    try:
        violations = neo.find_work_dedup_violations()
    finally:
        neo.close()

    logger.info("--- Work dedup audit (Neo4j) ---")
    if not violations:
        logger.info(
            "OK: no duplicate Work clusters by doi / openalex_id / fingerprint / arxiv_id",
        )
        return
    logger.info("Found %s duplicate cluster(s):", len(violations))
    for item in violations:
        logger.info(
            "  [%s] key=%r work_ids=%s",
            item["kind"],
            item["dedup_key"],
            item["work_ids"],
        )
