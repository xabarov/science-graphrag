"""Smoke tests for Neo4j storage facade after split."""


def test_neo4j_graph_store_import_paths() -> None:
    """All import paths must work after the split."""
    from science_graphrag.storage.neo4j import Neo4jGraphStore as package_store
    from science_graphrag.storage.neo4j.facade import Neo4jGraphStore as facade_store
    from science_graphrag.storage.neo4j_store import Neo4jGraphStore as shim_store

    assert shim_store is facade_store
    assert shim_store is package_store


def test_neo4j_graph_store_has_all_public_methods() -> None:
    """Facade must expose the same public API as the original store."""
    expected_methods = [
        "find_work_id_by_doi",
        "find_work_id_by_fingerprint",
        "find_work_id_by_arxiv",
        "work_exists",
        "work_has_incoming_cites",
        "upsert_work_layer1",
        "merge_cites",
        "merge_related_version",
        "upsert_minimal_work",
        "sync_work_semantic_layer",
        "merge_work_into_canonical",
        "merge_author_into_canonical",
        "upsert_claims_with_evidence",
        "workspace_create",
        "workspace_list",
        "workspace_get",
        "workspace_rename",
        "workspace_delete",
        "workspace_add_work",
        "workspace_remove_work",
        "workspace_merge_into",
        "ensure_schema",
        "close",
        "fulltext_search_work_ids",
        "find_work_dedup_violations",
        "get_work_external_keys",
        "detach_delete_work_if_no_incoming_cites",
        "fetch_work_bibliography_card",
        "cites_neighbor_work_ids",
        "list_workspace_authors",
        "fetch_author_affiliation_hint",
        "detach_delete_claims_for_work",
    ]
    from science_graphrag.storage.neo4j.facade import Neo4jGraphStore

    for method in expected_methods:
        assert hasattr(Neo4jGraphStore, method), f"Missing method: {method}"
