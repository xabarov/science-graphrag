"""VL PDF to Markdown ingestion (multimodal OpenAI-compatible API)."""

from __future__ import annotations

import base64
import json
import re
from collections.abc import Callable
from io import BytesIO
from pathlib import Path

from pdf2image import convert_from_path
from PIL import Image

from science_graphrag.config import Settings
from science_graphrag.ingestion.llm.raw_openai_transport import (
    ChatCompletionsNonJsonResponseError,
    post_chat_completions_json,
)
from science_graphrag.llm.concurrency import llm_pool_slot
from science_graphrag.observability.phoenix_tracer import SpanAttributes, llm_span
from science_graphrag.utils.project_logging import get_logger

DEFAULT_VL_PROMPT = (
    "Extract the document text faithfully as Markdown. "
    "Preserve headings, paragraphs, lists, tables where possible, authors, affiliations, "
    "references, and URLs. Output only the document content in Markdown."
)

CONTINUE_VL_PROMPT = (
    "Continue extracting the document text faithfully as Markdown (next page batch). "
    "Do not repeat content already extracted. "
    "Preserve headings, paragraphs, lists, tables, references, and URLs. "
    "Output only the document content in Markdown."
)

logger = get_logger("ingestion.vl_pdf")

_FENCE_RE = re.compile(r"^\s*```(?:json|md|markdown)?\s*$", re.IGNORECASE)


class VLAPIError(RuntimeError):
    """Raised when VL transport returns an unexpected payload shape."""


def _strip_common_markdown_fences(text: str) -> str:
    """Remove a single leading/trailing triple-backtick fence if present."""
    lines = text.splitlines()
    if not lines:
        return text
    if _FENCE_RE.match(lines[0]):
        lines = lines[1:]
    if lines and _FENCE_RE.match(lines[-1]):
        lines = lines[:-1]
    return "\n".join(lines).strip()


class VLPDFProcessor:  # pylint: disable=too-few-public-methods
    """OpenRouter-compatible VL PDF-to-Markdown processor with page-batching support."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.last_pages_total: int | None = None
        self.last_pages_processed: int | None = None
        self.last_batch_count: int | None = None

    def _pdf_pages(self, path: Path) -> list[Image.Image]:
        pages = convert_from_path(str(path), dpi=self.settings.vl_dpi)
        if self.settings.vl_max_pages > 0:
            pages = pages[: self.settings.vl_max_pages]
        return pages

    @staticmethod
    def _image_to_data_url(img: Image.Image) -> str:
        buf = BytesIO()
        img.save(buf, format="PNG")
        encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{encoded}"

    def _call_vl_api(self, images: list[Image.Image], prompt: str) -> tuple[str, dict]:
        """Send one batch of images to the VL API. Returns (markdown, usage)."""
        content: list[dict[str, object]] = []
        for img in images:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": self._image_to_data_url(img)},
                }
            )
        content.append({"type": "text", "text": prompt})

        payload = {
            "model": self.settings.vl_model,
            "messages": [{"role": "user", "content": content}],
            "temperature": 0.0,
            "max_tokens": self.settings.vl_max_tokens,
        }

        key = (self.settings.resolved_vl_api_key or "").strip()
        with llm_pool_slot("vl_pdf", self.settings):
            try:
                data, usage = post_chat_completions_json(
                    base_url=self.settings.vl_base_url,
                    api_key=key,
                    json_body=payload,
                    timeout_seconds=300.0,
                )
            except ChatCompletionsNonJsonResponseError:
                # post_chat_completions_json already includes a short preview in the message.
                logger.warning("VL chat.completions returned non-JSON body (%s)", prompt[:40])
                raise

        try:
            msg = data["choices"][0]["message"]
            content = msg["content"]
        except Exception as exc:  # noqa: BLE001
            raise VLAPIError(f"unexpected VL response shape: keys={list(data.keys())}") from exc

        if isinstance(content, str):
            # Some providers may return JSON-encoded string content.
            candidate = content.strip()
            if candidate.startswith("{") and "\"choices\"" in candidate:
                try:
                    inner = json.loads(candidate)
                    msg2 = inner["choices"][0]["message"]
                    content = msg2["content"]
                except Exception:  # noqa: BLE001
                    pass

        if isinstance(content, list):
            # Multimodal segments: join text parts only.
            parts: list[str] = []
            for seg in content:
                if isinstance(seg, dict) and seg.get("type") == "text":
                    t = seg.get("text")
                    if isinstance(t, str) and t.strip():
                        parts.append(t)
            text_out = "\n".join(parts).strip()
            if not text_out:
                raise VLAPIError("VL returned content[] without text segments")
            return _strip_common_markdown_fences(text_out), usage

        if not isinstance(content, str) or not content.strip():
            raise VLAPIError(f"VL returned empty/invalid message content: {type(content).__name__}")

        return _strip_common_markdown_fences(content.strip()), usage

    def pdf_to_markdown(  # pylint: disable=too-many-locals
        self,
        path: Path,
        *,
        on_page_progress: Callable[[int, int], None] | None = None,
        on_batches_ready: Callable[[int, int, int], None] | None = None,
    ) -> str:
        """Render ``path`` to Markdown using the configured VL model (page batches).

        ``on_batches_ready(batch_count, page_count, batch_size)`` runs once after batching.
        ``on_page_progress(pages_done, page_total)`` runs before each VL HTTP call (pages from
        prior batches only) and again after each batch completes.
        """
        if not self.settings.resolved_vl_api_key:
            raise ValueError("VL API key is not configured")

        all_pages = self._pdf_pages(path)
        if not all_pages:
            raise ValueError("No pages available for VL processing")

        batch_size = (
            self.settings.vl_batch_size if self.settings.vl_batch_size > 0 else len(all_pages)
        )
        batches = [all_pages[i : i + batch_size] for i in range(0, len(all_pages), batch_size)]

        self.last_pages_total = len(all_pages)
        self.last_pages_processed = len(all_pages)
        self.last_batch_count = len(batches)

        if on_batches_ready is not None:
            try:
                on_batches_ready(len(batches), len(all_pages), int(batch_size))
            except Exception:  # noqa: BLE001
                pass

        parts: list[str] = []
        total_prompt_tokens = 0
        total_completion_tokens = 0

        vl_transport_s = 300.0
        with llm_span(
            "llm.vl_pdf",
            {
                **SpanAttributes.llm_runtime_policy_attributes(
                    pool_name="vl_pdf",
                    transport_timeout_seconds=vl_transport_s,
                    timeout_contract="transport_only",
                    retry_extra_budget=2,
                    transport_max_attempts=3,
                ),
                "vl.model": self.settings.vl_model,
                "vl.base_url": self.settings.vl_base_url,
                "pdf.path": str(path),
                "vl.pages_total": len(all_pages),
                "vl.batch_count": len(batches),
                "vl.batch_size": batch_size,
            },
        ):
            for batch_idx, batch in enumerate(batches):
                prompt = DEFAULT_VL_PROMPT if batch_idx == 0 else CONTINUE_VL_PROMPT
                pages_done_before = sum(len(batches[j]) for j in range(batch_idx))
                if on_page_progress is not None:
                    try:
                        on_page_progress(pages_done_before, len(all_pages))
                    except Exception:  # noqa: BLE001
                        pass
                markdown_part, usage = self._call_vl_api(batch, prompt)
                parts.append(markdown_part)

                total_prompt_tokens += usage.get("prompt_tokens") or 0
                total_completion_tokens += usage.get("completion_tokens") or 0
                if on_page_progress is not None:
                    done_pages = sum(len(batches[j]) for j in range(batch_idx + 1))
                    try:
                        on_page_progress(done_pages, len(all_pages))
                    except Exception:  # noqa: BLE001
                        pass

            markdown = "\n\n".join(parts)

            SpanAttributes.set_llm_attrs(
                model=self.settings.vl_model,
                base_url=self.settings.vl_base_url,
                temperature=0.0,
                max_tokens=self.settings.vl_max_tokens,
            )
            SpanAttributes.set_llm_invocation_parameters(
                {
                    "max_tokens": self.settings.vl_max_tokens,
                    "pages": len(all_pages),
                    "dpi": self.settings.vl_dpi,
                    "batches": len(batches),
                    "batch_size": batch_size,
                }
            )
            SpanAttributes.set_llm_input_messages(
                [
                    {
                        "role": "user",
                        "content": (
                            f"<{len(all_pages)} page(s) in {len(batches)} " "batch(es)> + VL prompt"
                        ),
                    }
                ]
            )
            SpanAttributes.set_llm_output_messages([{"role": "assistant", "content": markdown}])

            if total_prompt_tokens or total_completion_tokens:
                SpanAttributes.set_llm_token_counts(
                    prompt_tokens=total_prompt_tokens or None,
                    completion_tokens=total_completion_tokens or None,
                    total_tokens=(total_prompt_tokens + total_completion_tokens) or None,
                    usage_source="api",
                )
            else:
                SpanAttributes.set_llm_token_counts_from_text(
                    prompt_text=DEFAULT_VL_PROMPT,
                    completion_text=markdown,
                )

            return markdown
