"""External PDF read tool (bounded download + extraction + bounded TTL cache)."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from science_graphrag.agent.pdf_read_contract import PDF_READ_DEFAULT_EXCERPT_CHARS
from science_graphrag.agent.tools.base import ToolResult
from science_graphrag.agent.tools.external.pdf_read_orchestrator import execute_pdf_read
from science_graphrag.agent.tools.trace_wrappers import run_tool_result_with_span
from science_graphrag.config import Settings

_PDF_READ_TRACE_URL_PREVIEW_CHARS = 300
_PDF_READ_MAX_EXCERPT_CHARS = 16_000
_PDF_READ_MAX_URL_CHARS = 2048


class ReadExternalPdfArgs(BaseModel):
    """Arguments for ``read_external_pdf``."""

    pdf_url: str = Field(..., min_length=8, max_length=_PDF_READ_MAX_URL_CHARS)
    max_excerpt_chars: int = Field(
        default=PDF_READ_DEFAULT_EXCERPT_CHARS,
        ge=512,
        le=_PDF_READ_MAX_EXCERPT_CHARS,
    )
    allowed_domains: list[str] | None = Field(
        default=None,
        description="Deprecated: ignored server-side (outbound policy is enforced by the server).",
    )
    blocked_domains: list[str] | None = Field(
        default=None,
        description="Deprecated: ignored server-side (outbound policy is enforced by the server).",
    )


def build_pdf_read_tools(*, settings: Settings) -> list[Any]:
    """Build external PDF read tool(s)."""

    @tool("read_external_pdf", args_schema=ReadExternalPdfArgs, return_direct=False)
    def read_external_pdf_tool(
        pdf_url: str,
        max_excerpt_chars: int = PDF_READ_DEFAULT_EXCERPT_CHARS,
        allowed_domains: list[str] | None = None,  # noqa: ARG001
        blocked_domains: list[str] | None = None,  # noqa: ARG001
    ) -> dict[str, Any]:
        """Read text excerpt from a public HTTPS PDF using bounded download/parsing."""
        _ = allowed_domains
        _ = blocked_domains

        def _run() -> ToolResult:
            pl = execute_pdf_read(
                pdf_url,
                settings=settings,
                max_excerpt_chars=max_excerpt_chars,
                job_id=None,
            )
            return ToolResult(payload=pl, row_count=int(pl.get("row_count") or 0))

        res = run_tool_result_with_span(
            tool_name="read_external_pdf",
            tool_parameters={
                "pdf_url": str(pdf_url or "")[:_PDF_READ_TRACE_URL_PREVIEW_CHARS],
                "max_excerpt_chars": int(max_excerpt_chars),
            },
            fn=_run,
        )
        return dict(res.payload)

    return [read_external_pdf_tool]


__all__ = ["ReadExternalPdfArgs", "build_pdf_read_tools"]
