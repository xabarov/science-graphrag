"""Dramatiq worker entry point for ingest jobs."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import AgeLimit, Retries, TimeLimit

from science_graphrag.api.ingest.registry import _registry
from science_graphrag.config import get_settings
from science_graphrag.worker.otel_middleware import OtelTraceMiddleware

logger = logging.getLogger(__name__)
settings = get_settings()

_broker = RedisBroker(url=settings.redis_url)
_broker.middleware = [
    mw for mw in _broker.middleware if not isinstance(mw, (Retries, AgeLimit, TimeLimit))
]
_broker.add_middleware(OtelTraceMiddleware())
_broker.add_middleware(Retries(max_retries=2))
_broker.add_middleware(AgeLimit(max_age=3 * 60 * 60 * 1000))
_broker.add_middleware(TimeLimit(time_limit=60 * 60 * 1000))
dramatiq.set_broker(_broker)

from science_graphrag.worker.actor import ingest_document_actor  # noqa: E402,F401


def run_compensation_sweep() -> None:
    """Re-enqueue jobs that stayed queued for too long."""
    registry = _registry(settings)
    registry.bootstrap()
    cutoff = datetime.now(UTC) - timedelta(seconds=60)
    for job in registry.list_stale_queued_jobs(before=cutoff):
        logger.info("Compensation sweep: re-enqueue job_id=%s", job.job_id)
        ingest_document_actor.send(job.job_id)


def run() -> None:
    """Start Dramatiq worker process."""
    from dramatiq.cli import main as dramatiq_main  # pylint: disable=import-outside-toplevel

    run_compensation_sweep()
    dramatiq_main(["dramatiq", "science_graphrag.worker.actor"])
