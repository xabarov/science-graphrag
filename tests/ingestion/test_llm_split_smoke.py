def test_prompts_modules_importable():
    from science_graphrag.ingestion.llm.prompts import authorships, metadata, references, semantic

    assert hasattr(metadata, "SYSTEM_FENCE")
    assert hasattr(references, "INSTRUCTION_BASE")
    assert hasattr(authorships, "USER_PROMPT_TEMPLATE")
    assert hasattr(semantic, "SYSTEM_SEMANTIC")


def test_heuristics_modules_importable():
    from science_graphrag.ingestion.llm.heuristics import (
        authorships,
        metadata,
        references,
        semantic,
    )

    assert callable(references.merge_reference_sets)
    assert callable(metadata.work_acceptable)
    assert callable(authorships.llm_authorships_need_fallback)
    assert callable(semantic.semantic_empty)


def test_executor_importable():
    from science_graphrag.ingestion.llm.executor import run_extraction

    assert callable(run_extraction)


def test_orchestrator_importable():
    from science_graphrag.ingestion.llm.orchestrator import extract_document_stages

    assert callable(extract_document_stages)


def test_public_api_unchanged():
    from science_graphrag.ingestion.llm import SyncInstructorExtractor, extract_stages_llm_first

    assert SyncInstructorExtractor is not None
    assert callable(extract_stages_llm_first)
