"""Benchmark route access to the active task store (supports test monkeypatching)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from science_graphrag.api.benchmark_task_store_core import BenchmarkTaskStore


def task_store() -> "BenchmarkTaskStore":
    """Return ``science_graphrag.api.benchmark.task_store`` (may be replaced in tests)."""

    from science_graphrag.api import benchmark as benchmark_pkg

    return benchmark_pkg.task_store  # type: ignore[attr-defined,no-any-return]
