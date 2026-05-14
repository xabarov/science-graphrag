"""In-memory task store for benchmark runs (facade).

Implementation: :mod:`science_graphrag.api.benchmark_task_store_core`.
"""

from __future__ import annotations

from science_graphrag.api.benchmark_task_store_core import BenchmarkTaskStore
from science_graphrag.api.task_benchmark_models import (
    FULL_RUN_BLOCK_DETAIL,
    RunPayloadTooLargeError,
    RunStatus,
)
from science_graphrag.storage.benchmark_run_persistence import BenchmarkRunPersistencePort

task_store = BenchmarkTaskStore(max_workers=2)


def attach_benchmark_run_persistence(port: BenchmarkRunPersistencePort) -> None:
    """Wire global ``task_store`` to app registry persistence (API lifespan)."""
    task_store.set_persistence(port)


__all__ = [
    "FULL_RUN_BLOCK_DETAIL",
    "BenchmarkTaskStore",
    "RunPayloadTooLargeError",
    "RunStatus",
    "attach_benchmark_run_persistence",
    "task_store",
]
