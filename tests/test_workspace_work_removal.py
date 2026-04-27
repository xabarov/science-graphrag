"""Unit tests for workspace work removal orchestration."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from science_graphrag.api.deps import build_store_registry_for_tests
from science_graphrag.api.workspace_work_removal import remove_work_from_workspace_result
from science_graphrag.config import Settings


def _stores(
    neo: MagicMock, chunks: MagicMock | None = None, works: MagicMock | None = None
) -> object:
    return build_store_registry_for_tests(
        neo4j=neo,
        qdrant_chunks=chunks or MagicMock(),
        qdrant_works=works or MagicMock(),
        qdrant_claims=MagicMock(),
        blob=MagicMock(),
        artifacts=MagicMock(),
        benchmark_runs=MagicMock(),
    )


def test_remove_detached_when_other_workspace_membership() -> None:
    neo = MagicMock()
    neo.workspace_get.side_effect = [
        {"id": "ws1", "name": "A", "work_ids": ["w1"], "unbounded": False},
        {"id": "ws1", "name": "A", "work_ids": [], "unbounded": False},
    ]
    neo.workspace_remove_work.return_value = True
    neo.count_work_workspace_memberships.return_value = 1
    neo.work_has_incoming_cites.return_value = False
    chunks = MagicMock()
    works = MagicMock()
    stores = _stores(neo, chunks, works)
    settings = Settings()
    out = remove_work_from_workspace_result(
        stores,
        settings=settings,
        workspace_id="ws1",
        work_id="w1",
    )
    assert out["removal_status"] == "detached_only"
    assert out["has_other_workspace_memberships"] is True
    chunks.remove_workspace_from_chunks.assert_called_once_with(work_id="w1", workspace_id="ws1")
    works.remove_workspace_from_work_point.assert_called_once_with(work_id="w1", workspace_id="ws1")
    neo.detach_delete_work_if_no_incoming_cites.assert_not_called()


def test_remove_purge_blocked_when_incoming_cites() -> None:
    neo = MagicMock()
    neo.workspace_get.side_effect = [
        {"id": "ws1", "name": "A", "work_ids": ["w1"], "unbounded": False},
        {"id": "ws1", "name": "A", "work_ids": [], "unbounded": False},
    ]
    neo.workspace_remove_work.return_value = True
    neo.count_work_workspace_memberships.return_value = 0
    neo.work_has_incoming_cites.return_value = True
    stores = _stores(neo)
    settings = Settings()
    out = remove_work_from_workspace_result(
        stores,
        settings=settings,
        workspace_id="ws1",
        work_id="w1",
    )
    assert out["removal_status"] == "purge_blocked_by_incoming_cites"
    assert out["has_incoming_cites"] is True
    neo.detach_delete_work_if_no_incoming_cites.assert_not_called()


def test_remove_purged_when_isolated(monkeypatch: pytest.MonkeyPatch) -> None:
    neo = MagicMock()
    neo.workspace_get.side_effect = [
        {"id": "ws1", "name": "A", "work_ids": ["w1"], "unbounded": False},
        {"id": "ws1", "name": "A", "work_ids": [], "unbounded": False},
        {"id": "ws1", "name": "A", "work_ids": [], "unbounded": False},
    ]
    neo.workspace_remove_work.return_value = True
    neo.count_work_workspace_memberships.return_value = 0
    neo.work_has_incoming_cites.return_value = False
    neo.work_exists.return_value = True
    neo.detach_delete_work_if_no_incoming_cites.return_value = True
    chunks = MagicMock()
    works = MagicMock()
    claims = MagicMock()
    stores = build_store_registry_for_tests(
        neo4j=neo,
        qdrant_chunks=chunks,
        qdrant_works=works,
        qdrant_claims=claims,
        blob=MagicMock(),
        artifacts=MagicMock(),
        benchmark_runs=MagicMock(),
    )
    settings = Settings()
    monkeypatch.setattr(
        "science_graphrag.api.workspace_work_removal._purge_postgres_for_work",
        lambda *_a, **_k: None,
    )
    out = remove_work_from_workspace_result(
        stores,
        settings=settings,
        workspace_id="ws1",
        work_id="w1",
    )
    assert out["removal_status"] == "purged"
    claims.delete_points_by_work_id.assert_called_once_with(work_id="w1")
    chunks.delete_points_by_work_id.assert_called_once_with(work_id="w1")
    works.delete_by_work_id.assert_called_once_with(work_id="w1")
    neo.detach_delete_claims_for_work.assert_called_once_with("w1")
    neo.detach_delete_work_if_no_incoming_cites.assert_called_once_with("w1")


def test_remove_unbounded_never_purges() -> None:
    neo = MagicMock()
    neo.workspace_get.side_effect = [
        {"id": "ws1", "name": "Corpus", "work_ids": ["w1"], "unbounded": True},
        {"id": "ws1", "name": "Corpus", "work_ids": ["w1"], "unbounded": True},
    ]
    neo.workspace_remove_work.return_value = False
    neo.work_has_incoming_cites.return_value = False
    stores = _stores(neo)
    settings = Settings()
    out = remove_work_from_workspace_result(
        stores,
        settings=settings,
        workspace_id="ws1",
        work_id="w1",
    )
    assert out["removal_status"] == "detached_only"
    neo.count_work_workspace_memberships.assert_not_called()
    neo.detach_delete_work_if_no_incoming_cites.assert_not_called()


def test_remove_raises_when_work_not_in_workspace() -> None:
    neo = MagicMock()
    neo.workspace_get.return_value = {
        "id": "ws1",
        "name": "A",
        "work_ids": ["w2"],
        "unbounded": False,
    }
    stores = _stores(neo)
    settings = Settings()
    with pytest.raises(ValueError, match="work_not_in_workspace"):
        remove_work_from_workspace_result(
            stores,
            settings=settings,
            workspace_id="ws1",
            work_id="w1",
        )
