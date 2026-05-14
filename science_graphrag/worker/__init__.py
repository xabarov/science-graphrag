"""Dramatiq worker entry point for ingest jobs."""

from __future__ import annotations

import logging
import os
import sys
from datetime import UTC, datetime, timedelta

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import AgeLimit, Retries, TimeLimit

from science_graphrag.config import get_settings
from science_graphrag.ingestion.jobs.registry import get_ingest_job_registry
from science_graphrag.utils.project_logging import configure_logging
from science_graphrag.worker.otel_middleware import OtelTraceMiddleware
from science_graphrag.worker.trace_options import dramatiq_otel_options

logger = logging.getLogger(__name__)
settings = get_settings()

_broker = RedisBroker(url=settings.redis_url)
_broker.middleware = [
    mw for mw in _broker.middleware if not isinstance(mw, (Retries, AgeLimit, TimeLimit))
]
_broker.add_middleware(OtelTraceMiddleware())
_broker.add_middleware(Retries(max_retries=2))
# Redis AOF can resurrect old queue entries across long downtime; 3h caused skipped
# messages while DB rows stayed "queued". Use a generous cap for ingest latency.
_INGEST_MESSAGE_MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000
_broker.add_middleware(AgeLimit(max_age=_INGEST_MESSAGE_MAX_AGE_MS))
_broker.add_middleware(TimeLimit(time_limit=60 * 60 * 1000))
dramatiq.set_broker(_broker)

configure_logging()

from science_graphrag.worker.actor import ingest_document_actor  # noqa: E402,F401


def run_compensation_sweep() -> None:
    """Recover stale ``running`` rows, then re-enqueue ``queued`` jobs stuck without delivery."""
    registry = get_ingest_job_registry(settings)
    registry.bootstrap()
    # Orphan ``running`` rows (worker died / Dramatiq AgeLimit skip) block the actor; reset first.
    stale_running_cutoff = datetime.now(UTC) - timedelta(hours=2)
    for job_id in registry.reset_stale_running_jobs_to_queued(before=stale_running_cutoff):
        logger.info("Compensation sweep: reset stale running -> queued job_id=%s", job_id)
    # Re-enqueue jobs that missed delivery (enqueue race, aged-out message, etc.).
    # Keep small so a restart recovers quickly without waiting 60s past creation.
    cutoff = datetime.now(UTC) - timedelta(seconds=10)
    for job in registry.list_stale_queued_jobs(before=cutoff):
        logger.info("Compensation sweep: re-enqueue job_id=%s", job.job_id)
        otel_opts = dramatiq_otel_options()
        if otel_opts:
            ingest_document_actor.send_with_options(args=(job.job_id,), **otel_opts)
        else:
            ingest_document_actor.send(job.job_id)


def run() -> None:
    """Start Dramatiq worker process."""
    from dramatiq.cli import main as dramatiq_main  # pylint: disable=import-outside-toplevel
    from dramatiq.cli import (
        make_argument_parser,
    )

    run_compensation_sweep()
    # Dramatiq 2.x: cli.main() expects a Namespace from argparse, not a raw argv list.
    parser = make_argument_parser()
    if len(sys.argv) > 1:
        cli_argv = ["science_graphrag.worker.actor", *sys.argv[1:]]
    else:
        extra: list[str] = []
        procs = os.getenv("SCIENCE_GRAPHRAG_DRAMATIQ_PROCESSES", "").strip()
        if procs:
            extra.extend(["--processes", procs])
        thr = os.getenv("SCIENCE_GRAPHRAG_DRAMATIQ_THREADS", "").strip()
        if thr:
            extra.extend(["--threads", thr])
        cli_argv = ["science_graphrag.worker.actor", *extra]
    args = parser.parse_args(cli_argv)
    raise SystemExit(dramatiq_main(args))
