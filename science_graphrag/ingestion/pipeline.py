from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from science_graphrag.config import Settings, get_settings
from science_graphrag.observability.phoenix_tracer import chain_span, init_tracer_provider
from science_graphrag.domain.models import WorkDraft
from science_graphrag.ingestion.embeddings import HashEmbeddingProvider, try_sentence_transformer
from science_graphrag.ingestion.enrichment.openalex import draft_from_openalex, fetch_work_by_doi
from science_graphrag.ingestion.normalize import chunk_text, normalize_text
from science_graphrag.ingestion.pdf import extract_text_from_pdf
from science_graphrag.ingestion.stages.authorships import extract_authorships
from science_graphrag.ingestion.stages.metadata import extract_metadata, merge_draft_prefer_enriched
from science_graphrag.ingestion.stages.references import extract_references
from science_graphrag.ingestion.vl_pdf import VLPDFProcessor
from science_graphrag.storage.blobs import BlobStore
from science_graphrag.storage.db import init_db
from science_graphrag.storage.models_orm import DocumentRecord, IngestionRunRecord
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.qdrant_store import QdrantChunkStore


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug or "document"


def _markdown_from_path(path: Path, settings: Settings) -> tuple[str, str]:
    suf = path.suffix.lower()
    if suf != ".pdf":
        return path.read_text(encoding="utf-8", errors="replace"), "plain-text"

    with chain_span(
        "pdf_to_markdown",
        {"use_vl": settings.use_vl_for_pdf, "path": path.name},
    ):
        if settings.use_vl_for_pdf:
            try:
                markdown = VLPDFProcessor(settings).pdf_to_markdown(path)
                return markdown, "vl"
            except Exception:
                pass

        return extract_text_from_pdf(path), "pypdf-fallback"


def _resolve_work_id(neo: Neo4jGraphStore, draft: WorkDraft) -> str:
    if draft.doi:
        ex = neo.find_work_id_by_doi(draft.doi)
        if ex:
            return ex
    if draft.arxiv_id:
        ex = neo.find_work_id_by_arxiv(draft.arxiv_id)
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


def _institution_nodes_from_authorships(
    authorships,
) -> list[tuple[str, str, str | None]]:
    nodes: list[tuple[str, str, str | None]] = []
    for authorship in authorships:
        affiliation = next((value for value in authorship.raw_affiliations if value.strip()), None)
        if not affiliation:
            continue
        clean = affiliation.strip()
        inst_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "institution:" + clean.lower()))
        nodes.append((inst_id, clean, None))
    return nodes


def _write_markdown_artifact(
    *,
    settings: Settings,
    document_id: str,
    source_path: Path,
    markdown: str,
    extraction_mode: str,
) -> Path:
    artifact_store = BlobStore(settings.artifact_root)
    slug = _slug(source_path.stem)
    artifact_rel = Path("ingestion") / document_id / slug / "article.md"
    header = f"<!-- source={source_path.name} extraction_mode={extraction_mode} -->\n\n"
    return artifact_store.write_artifact(artifact_rel, header + markdown)


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
    blob_store = BlobStore(settings.blob_root)
    sha, _stored = blob_store.store_file(path)
    with chain_span("ingest_document", {"document_id": doc_id, "source": str(path.resolve())}):
        markdown_text, extraction_mode = _markdown_from_path(path, settings)
        _artifact_path = _write_markdown_artifact(
            settings=settings,
            document_id=doc_id,
            source_path=path,
            markdown=markdown_text,
            extraction_mode=extraction_mode,
        )
        normalized = normalize_text(markdown_text)
        blob_store.write_text("extracted.txt", normalized)

        with chain_span("metadata_and_references_extraction"):
            draft = extract_metadata(normalized)
            authorships = extract_authorships(normalized)
            references = extract_references(normalized)

        with chain_span("openalex_enrichment"):
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
            with chain_span("neo4j_graph_persistence"):
                neo.ensure_schema()
                work_id = _resolve_work_id(neo, draft)
                vid = _venue_id(draft.venue_name)
                inst_nodes = _institution_nodes_from_authorships(authorships)

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
            with chain_span(
                "qdrant_vector_upsert",
                {"chunks": len(chunks), "embedding": settings.embedding_model or "hash"},
            ):
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
                    mime_type=f"application/{path.suffix.lower().lstrip('.') or 'octet-stream'}",
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
    init_tracer_provider()
    s = get_settings()
    engine = create_engine(s.database_url, pool_pre_ping=True)
    init_db(engine)
    factory = sessionmaker(bind=engine)
    with factory() as session:
        with session.begin():
            doc_id, work_id = ingest_document(path, settings=s, session=session)
        print(f"document_id={doc_id} work_id={work_id}")
