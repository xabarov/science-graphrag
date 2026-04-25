"""Unit tests for entity dedup pipelines (Wave T)."""


def test_institution_embed_text():
    from science_graphrag.dedup.institution_pipeline import embed_text

    text = embed_text({"normalized_name": "MIT", "country": "US", "city": "Cambridge"})
    assert "MIT" in text and "US" in text


def test_venue_embed_text():
    from science_graphrag.dedup.venue_pipeline import embed_text

    text = embed_text({"normalized_name": "NeurIPS", "venue_type": "conference"})
    assert "NeurIPS" in text


def test_method_embed_text():
    from science_graphrag.dedup.method_pipeline import embed_text

    text = embed_text(
        {
            "normalized_name": "BERT",
            "aliases": ["bert-base", "bert-large"],
            "description_short": "Transformer LM",
        },
    )
    assert "BERT" in text and "bert-base" in text


def test_dataset_embed_text():
    from science_graphrag.dedup.dataset_pipeline import embed_text

    text = embed_text({"normalized_name": "ImageNet", "aliases": ["ILSVRC"]})
    assert "ImageNet" in text


def test_entity_dedup_conflict_orm_fields():
    from science_graphrag.storage.models_orm import EntityDedupConflict

    assert hasattr(EntityDedupConflict, "entity_type")
    assert hasattr(EntityDedupConflict, "entity_id_a")
    assert hasattr(EntityDedupConflict, "entity_id_b")
    assert hasattr(EntityDedupConflict, "similarity_score")
    assert hasattr(EntityDedupConflict, "status")
