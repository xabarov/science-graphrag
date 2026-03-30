"""
Project-wide logging for ingestion and LLM extraction.

Uses stdlib logging only (no stdout spam); level from SCIENCE_GRAPHRAG_LOG_LEVEL.
"""

from __future__ import annotations

import logging
import os
import sys

_CONFIGURED = False


def configure_logging() -> None:
    """Idempotent root handler for science_graphrag.* loggers."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    level_name = os.getenv("SCIENCE_GRAPHRAG_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(fmt)
    root_sg = logging.getLogger("science_graphrag")
    root_sg.setLevel(level)
    if not root_sg.handlers:
        root_sg.addHandler(handler)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Logger under ``science_graphrag.<name>``."""
    configure_logging()
    return logging.getLogger(f"science_graphrag.{name}")
