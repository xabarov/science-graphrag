from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from science_graphrag.config import Settings, get_settings
from science_graphrag.domain.models import WorkDraft
from science_graphrag.ingestion.embeddings import HashEmbeddingProvider, try_sentence_transformer
from science_graphrag.ingestion.enrichment.openalex import draft_from_openalex, fetch_work_by_doi
from science_graphrag.ingestion.normalize import chunk_text, normalize_text
from science_graphrag.ingestion.pdf import extract_text_from_pdf
from science_graphrag.ingestion.stages.authorships import extract_authorships
from science_graphrag.ingestion.stages.metadata import extract_metadata, merge_draft_prefer_enriched
from science_graphrag.ingestion.stages.references import extract_references
from science_graphrag.storage.blobs import BlobStore
from science_graphrag.storage.db import init_db
from science_graphrag.storage.models_orm import DocumentRecord, IngestionRunRecord
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.qdrant_store import QdrantChunkStore


def _text_from_path(path: Path) -> str:
    suf = path.suffix.lower()
    if suf == ".pdf":
        return extract_text_from_pdf(path)
    return path.read_text(encoding="utf-8", errors="replace")


def _resolve_work_id(neo: Neo4jGraphStore, draft: WorkDraft) -> str:
    if draft.doi:
        ex = neo.find_work_id_by_doi(draft.doi)
        if ex:
            return ex
    if draft.fingerprint:
        ex = neo.find_work_id_by_fingerprint(draft.fingerprint)
        if ex:
            return ex
    return str(uuid.uuid4())


def _venue_id(name: str | None) -> str | None:
    if not name:
        return None
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "venue:" + name.strip().lower()))


def ingest_document(
    path: Path,
    *,
    settings: Settings | None = None,
    session: Session | None = None,
) -> tuple[str, str]:
    """
    Ingest one PDF or text file. Returns (document_id, work_id).
    """
    settings = settings or get_settings()
    doc_id = str(uuid.uuid4())
    blob = BlobStore(settings.blob_root)
    sha, _stored = blob.store_file(path)
    raw_text = _text_from_path(path)
    blob.write_text("extracted.txt", normalize_text(raw_text))

    normalized = normalize_text(raw_text)
    draft = extract_metadata(normalized)
    authorships = extract_authorships(normalized)
    references = extract_references(normalized)

    if draft.doi:
        try:
            oa = fetch_work_by_doi(draft.doi, settings.openalex_mailto)
            if oa:
                enriched = draft_from_openalex(oa)
                draft = merge_draft_prefer_enriched(draft, enriched)
        except Exception:
            pass

    neo = Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    try:
        neo.ensure_schema()
        work_id = _resolve_work_id(neo, draft)
        vid = _venue_id(draft.venue_name)
        inst_nodes: list[tuple[str, str, str | None]] = []

        neo.upsert_work_layer1(
            work_id,
            draft,
            authorships,
            venue_id=vid,
            institution_nodes=inst_nodes,
        )

        for ref in references:
            if not ref.doi:
                continue
            try:
                oa = fetch_work_by_doi(ref.doi, settings.openalex_mailto)
            except Exception:
                oa = None
            if oa:
                cd = draft_from_openalex(oa)
                cid = _resolve_work_id(neo, cd)
                neo.upsert_minimal_work(
                    cid,
                    title=cd.title,
                    publication_year=cd.publication_year,
                    doi=cd.doi,
                    fingerprint=cd.fingerprint,
                    openalex_id=cd.openalex_id,
                    ingestion_confidence=cd.ingestion_confidence,
                )
            else:
                cid = str(uuid.uuid4())
                neo.upsert_minimal_work(
                    cid,
                    title=ref.title,
                    publication_year=ref.year,
                    doi=ref.doi,
                    fingerprint=None,
                    openalex_id=None,
                    ingestion_confidence=0.25,
                )
            neo.merge_cites(work_id, cid)

        chunks = chunk_text(normalized, settings.chunk_size, settings.chunk_overlap)
        embedder = (
            try_sentence_transformer(settings.embedding_model)
            if settings.embedding_model
            else HashEmbeddingProvider()
        )
        vectors = embedder.embed(chunks)
        q = QdrantChunkStore(
            settings.qdrant_url,
            settings.qdrant_collection,
            vector_dim=embedder.dim,
        )
        q.upsert_chunks(
            work_id=work_id,
            document_id=doc_id,
            chunks=chunks,
            vectors=vectors,
            embedding_model=settings.embedding_model or "hash-deterministic",
        )
    finally:
        neo.close()

    if session is not None:
        now = datetime.now(UTC)
        session.add(
            DocumentRecord(
                id=doc_id,
                sha256=sha,
                source_path=str(path.resolve()),
                mime_type=None,
            )
        )
        session.add(
            IngestionRunRecord(
                document_id=doc_id,
                status="completed",
                finished_at=now,
            )
        )

    return doc_id, work_id


def run_ingest_cli(path: Path) -> None:
    s = get_settings()
    engine = create_engine(s.database_url, pool_pre_ping=True)
    init_db(engine)
    factory = sessionmaker(bind=engine)
    with factory() as session:
        with session.begin():
            doc_id, work_id = ingest_document(path, settings=s, session=session)
        print(f"document_id={doc_id} work_id={work_id}")
