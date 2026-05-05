"""Runtime helpers for per-document ingest execution."""

from __future__ import annotations

import signal
from contextlib import contextmanager


@contextmanager
def file_timeout(seconds: int):
    """Raise TimeoutError when a single file ingest exceeds limit."""
    if seconds <= 0:
        yield
        return
    if not hasattr(signal, "SIGALRM"):
        yield
        return

    def _handler(_sig, _frame):
        raise TimeoutError(f"ingest_document exceeded {seconds}s")

    previous = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)
