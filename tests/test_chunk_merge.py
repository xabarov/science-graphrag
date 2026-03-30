from science_graphrag.ingestion.llm.chunk_merge import (
    aggregate_edge_provenance,
    entity_merge_key_author,
    entity_merge_key_work,
    merge_provenance_lists,
    relationship_dedup_key,
)


def test_merge_provenance_lists_order():
    assert merge_provenance_lists(["a", "b"], ["b", "c"]) == ["a", "b", "c"]


def test_entity_merge_key_work_priority():
    assert "doi" in entity_merge_key_work(
        doi="10.1000/182", arxiv_id="1234.5678", title_fingerprint=None
    )
    k = entity_merge_key_work(doi=None, arxiv_id="1234.5678", title_fingerprint="fp")
    assert "arxiv" in k


def test_relationship_dedup_key_normalizes_predicate():
    k = relationship_dedup_key("s", "CITES", "o")
    assert k[1] == "cites"


def test_aggregate_edge_provenance():
    p = aggregate_edge_provenance(None, ["c1"])
    p2 = aggregate_edge_provenance(p, ["c1", "c2"])
    assert set(p2["source_chunk_fingerprints"]) == {"c1", "c2"}


def test_entity_merge_key_author():
    k = entity_merge_key_author("Jane Doe", "MIT")
    assert "jane doe" in k
