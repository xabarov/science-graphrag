"""Thin Neo4jGraphStore method bodies delegating to ``reads`` / ``writes`` modules."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from science_graphrag.domain.models import AuthorshipDraft, WorkDraft
from science_graphrag.domain.semantic_models import SemanticExtractionV1
from science_graphrag.storage.neo4j import reads
from science_graphrag.storage.neo4j.writes import (
    claims,
    contradictions,
    dedup,
    institutions,
    semantic,
    venues,
    works,
    workspace,
)

if TYPE_CHECKING:
    from science_graphrag.ingestion.claims.models import ClaimDraft


class Neo4jGraphStoreDelegates:
    """Mixin of public API methods (combined with :class:`Neo4jGraphStoreBase`)."""

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

    def merge_work_contradicts(
        self,
        work_id_a: str,
        work_id_b: str,
        *,
        subtype: str = "unspecified",
    ) -> None:
        contradictions.merge_work_contradicts(self._client, work_id_a, work_id_b, subtype=subtype)

    def work_has_incoming_cites(self, work_id: str) -> bool:
        return reads.work_has_incoming_cites(self._client, work_id)

    def count_work_outgoing_cites(self, work_id: str) -> int:
        return reads.count_work_outgoing_cites(self._client, work_id)

    def count_work_workspace_memberships(self, work_id: str) -> int:
        return reads.count_work_workspace_memberships(self._client, work_id)

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

    def list_work_authors(self, work_id: str) -> list[dict[str, Any]]:
        return reads.list_work_authors(self._client, work_id)

    def fetch_author_display_name(self, author_id: str) -> str:
        return reads.fetch_author_display_name(self._client, author_id)

    def fetch_author_affiliation_hint(self, author_id: str) -> str:
        return reads.fetch_author_affiliation_hint(self._client, author_id)

    def list_work_institutions(self, work_id: str) -> list[dict[str, Any]]:
        return reads.list_work_institutions(self._client, work_id)

    def list_work_venues(self, work_id: str) -> list[dict[str, Any]]:
        return reads.list_work_venues(self._client, work_id)

    def list_work_methods(self, work_id: str) -> list[dict[str, Any]]:
        return reads.list_work_methods(self._client, work_id)

    def list_work_datasets(self, work_id: str) -> list[dict[str, Any]]:
        return reads.list_work_datasets(self._client, work_id)

    def list_workspace_institutions(self, workspace_id: str) -> list[dict[str, Any]]:
        return reads.list_workspace_institutions(self._client, workspace_id)

    def list_workspace_venues(self, workspace_id: str) -> list[dict[str, Any]]:
        return reads.list_workspace_venues(self._client, workspace_id)

    def list_workspace_methods(self, workspace_id: str) -> list[dict[str, Any]]:
        return reads.list_workspace_methods(self._client, workspace_id)

    def list_workspace_datasets(self, workspace_id: str) -> list[dict[str, Any]]:
        return reads.list_workspace_datasets(self._client, workspace_id)

    def fetch_entity_display_label(self, entity_type: str, entity_id: str) -> str:
        return reads.fetch_entity_display_label(self._client, entity_type, entity_id)

    def merge_institution_into_canonical(self, keep_id: str, drop_id: str) -> bool:
        return institutions.merge_institution(self._client, keep_id, drop_id, keep_id)

    def merge_venue_into_canonical(self, keep_id: str, drop_id: str) -> bool:
        return venues.merge_venue(self._client, keep_id, drop_id, keep_id)

    def add_method_alias(self, method_id: str, alias: str) -> bool:
        return semantic.add_method_alias(self._client, method_id, alias)

    def add_dataset_alias(self, dataset_id: str, alias: str) -> bool:
        return semantic.add_dataset_alias(self._client, dataset_id, alias)

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
