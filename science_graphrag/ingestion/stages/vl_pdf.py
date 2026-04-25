from __future__ import annotations

from pathlib import Path
from typing import Callable

from science_graphrag.ingestion.stage_context import IngestRunContext, IngestStage


def run_vl_pdf(
    ctx: IngestRunContext,
    *,
    source_path: Path,
    markdown_loader: Callable[[Path], tuple[str, str]],
) -> tuple[str, str]:
    with ctx.stage(IngestStage.PARSE_PDF):
        return markdown_loader(source_path)
