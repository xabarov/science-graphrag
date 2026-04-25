"""Neo4jGraphStore facade preserving backward-compatible public API."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from science_graphrag.domain.models import AuthorshipDraft, WorkDraft
from science_graphrag.domain.semantic_models import SemanticExtractionV1
from science_graphrag.storage.neo4j import reads, schema
from science_graphrag.storage.neo4j.client import _Neo4jClient
from science_graphrag.storage.neo4j.writes import claims, dedup, semantic, works, workspace

if TYPE_CHECKING:
    from science_graphrag.ingestion.claims.models import ClaimDraft


class _LegacyDriverClientAdapter:
    """Compatibility adapter for tests that monkeypatch `Neo4jGraphStore._driver`."""

    def __init__(self, driver: Any) -> None:
        self._driver = driver

    @contextmanager
    def session(self) -> Iterator[Any]:
        with self._driver.session() as session:
            yield session

    def close(self) -> None:
        self._driver.close()

    def wipe_all(self) -> None:
        with self._driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")


class Neo4jGraphStore:
    """Facade over neo4j subpackage. Public API matches legacy store."""

    def __init__(self, uri: str, user: str, password: str) -> None:
        self._client = _Neo4jClient(uri, user, password)

    @property
    def _client(self) -> _Neo4jClient | _LegacyDriverClientAdapter:  # type: ignore[misc]
        client = self.__dict__.get("__client")
        if client is not None:
            return client
        driver = self.__dict__.get("_driver")
        if driver is not None:
            return _LegacyDriverClientAdapter(driver)
        raise AttributeError("Neo4jGraphStore is not initialized")

    @_client.setter
    def _client(self, value: _Neo4jClient) -> None:
        self.__dict__["__client"] = value
        self.__dict__["_driver"] = value._driver  # legacy compatibility for tests

    def close(self) -> None:
        self._client.close()

    def session(self):
        return self._client.session()

    def wipe_all(self) -> None:
        self._client.wipe_all()

    def ensure_schema(self) -> None:
        schema.ensure_schema(self._client)

    def find_work_id_by_doi(self, doi: str) -> str | None:
        return reads.find_work_id_by_doi(self._client, doi)

    def find_work_id_by_fingerprint(self, fingerprint: str) -> str | None:
        return reads.find_work_id_by_fingerprint(self._client, fingerprint)

    def find_work_id_by_arxiv(self, arxiv_id: str) -> str | None:
        return reads.find_work_id_by_arxiv(self._client, arxiv_id)

    def get_work_external_keys(self, work_id: str) -> dict[str, str] | None:
        return reads.get_work_external_keys(self._client, work_id)

    def work_exists(self, work_id: str) -> bool:
        return reads.work_exists(self._client, work_id)

    def work_has_incoming_cites(self, work_id: str) -> bool:
        return reads.work_has_incoming_cites(self._client, work_id)

    def detach_delete_work_if_no_incoming_cites(self, work_id: str) -> bool:
        return works.detach_delete_work_if_no_incoming_cites(self._client, work_id)

    def upsert_work_layer1(
        self,
        work_id: str,
        draft: WorkDraft,
        authorships: list[AuthorshipDraft],
        venue_id: str | None,
        institution_nodes: list[tuple[str, str, list[str]]],
    ) -> None:
        works.upsert_work_layer1(
            self._client,
            work_id,
            draft,
            authorships,
            venue_id,
            institution_nodes,
        )

    def merge_cites(self, from_work_id: str, to_work_id: str) -> None:
        works.merge_cites(self._client, from_work_id, to_work_id)

    def merge_related_version(self, a_id: str, b_id: str) -> None:
        works.merge_related_version(self._client, a_id, b_id)

    def upsert_minimal_work(
        self,
        work_id: str,
        *,
        title: str | None,
        publication_year: int | None,
        doi: str | None,
        arxiv_id: str | None = None,
        fingerprint: str | None,
        openalex_id: str | None,
        ingestion_confidence: float,
    ) -> None:
        works.upsert_minimal_work(
            self._client,
            work_id,
            title=title,
            publication_year=publication_year,
            doi=doi,
            arxiv_id=arxiv_id,
            fingerprint=fingerprint,
            openalex_id=openalex_id,
            ingestion_confidence=ingestion_confidence,
        )

    def find_work_dedup_violations(self) -> list[dict[str, Any]]:
        return reads.find_work_dedup_violations(self._client)

    def sync_work_semantic_layer(
        self,
        work_id: str,
        extraction: SemanticExtractionV1,
        *,
        confidence_threshold: float = 0.35,
    ) -> None:
        semantic.sync_work_semantic_layer(
            self._client,
            work_id,
            extraction,
            confidence_threshold=confidence_threshold,
        )

    def merge_work_into_canonical(self, keep_id: str, drop_id: str) -> bool:
        return dedup.merge_work_into_canonical(self._client, keep_id, drop_id)

    def merge_author_into_canonical(self, keep_id: str, drop_id: str) -> bool:
        return dedup.merge_author_into_canonical(self._client, keep_id, drop_id)

    def fetch_work_bibliography_card(self, work_id: str) -> dict[str, Any] | None:
        return reads.fetch_work_bibliography_card(self._client, work_id)

    def fulltext_search_work_ids(self, query: str, *, limit: int = 20) -> list[tuple[str, float]]:
        return reads.fulltext_search_work_ids(self._client, query, limit=limit)

    def cites_neighbor_work_ids(
        self,
        seed_work_ids: list[str],
        *,
        exclude_ids: set[str],
        limit: int = 80,
    ) -> list[str]:
        return reads.cites_neighbor_work_ids(
            self._client,
            seed_work_ids,
            exclude_ids=exclude_ids,
            limit=limit,
        )

    def list_workspace_authors(self, workspace_id: str) -> list[dict[str, Any]]:
        return reads.list_workspace_authors(self._client, workspace_id)

    def fetch_author_affiliation_hint(self, author_id: str) -> str:
        return reads.fetch_author_affiliation_hint(self._client, author_id)

    def detach_delete_claims_for_work(self, work_id: str) -> None:
        claims.detach_delete_claims_for_work(self._client, work_id)

    def upsert_claims_with_evidence(self, work_id: str, claims_rows: list["ClaimDraft"]) -> None:
        claims.upsert_claims_with_evidence(self._client, work_id, claims_rows)

    def workspace_create(self, name: str) -> dict[str, Any]:
        return workspace.workspace_create(self._client, name)

    def workspace_list(self) -> list[dict[str, Any]]:
        return reads.workspace_list(self._client)

    def workspace_get(self, workspace_id: str) -> dict[str, Any] | None:
        return reads.workspace_get(self._client, workspace_id)

    def workspace_rename(self, workspace_id: str, name: str) -> bool:
        return workspace.workspace_rename(self._client, workspace_id, name)

    def workspace_delete(self, workspace_id: str) -> bool:
        return workspace.workspace_delete(self._client, workspace_id)

    def workspace_add_work(self, workspace_id: str, work_id: str) -> bool:
        return workspace.workspace_add_work(self._client, workspace_id, work_id)

    def workspace_remove_work(self, workspace_id: str, work_id: str) -> bool:
        return workspace.workspace_remove_work(self._client, workspace_id, work_id)

    def workspace_merge_into(self, keep_workspace_id: str, drop_workspace_id: str) -> bool:
        return workspace.workspace_merge_into(self._client, keep_workspace_id, drop_workspace_id)
