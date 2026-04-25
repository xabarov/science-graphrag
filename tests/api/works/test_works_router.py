from __future__ import annotations


def test_works_router_imports() -> None:
    from science_graphrag.api.works import router

    assert router is not None


def test_works_shim_imports() -> None:
    from science_graphrag.api.works import router as works_router

    assert works_router is not None


def test_graph_neighborhood_imports() -> None:
    from science_graphrag.api.works.graph_neighborhood import work_graph_neighborhood

    assert callable(work_graph_neighborhood)
