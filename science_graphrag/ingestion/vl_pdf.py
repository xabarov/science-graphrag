"""VL PDF to Markdown ingestion (multimodal OpenAI-compatible API)."""

from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path

from pdf2image import convert_from_path
from PIL import Image

from science_graphrag.config import Settings
from science_graphrag.ingestion.llm.raw_openai_transport import post_chat_completions_json
from science_graphrag.observability.phoenix_tracer import SpanAttributes, llm_span

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

        key = self.settings.vl_api_key or ""
        data, usage = post_chat_completions_json(
            base_url=self.settings.vl_base_url,
            api_key=key,
            json_body=payload,
            timeout_seconds=300.0,
        )

        return data["choices"][0]["message"]["content"], usage

    def pdf_to_markdown(self, path: Path) -> str:
        """Render ``path`` to Markdown using the configured VL model (page batches)."""
        if not self.settings.vl_api_key:
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

        parts: list[str] = []
        total_prompt_tokens = 0
        total_completion_tokens = 0

        with llm_span(
            "llm.vl_pdf",
            {
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
                markdown_part, usage = self._call_vl_api(batch, prompt)
                parts.append(markdown_part)

                total_prompt_tokens += usage.get("prompt_tokens") or 0
                total_completion_tokens += usage.get("completion_tokens") or 0

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
                            f"<{len(all_pages)} page(s) in {len(batches)} "
                            "batch(es)> + VL prompt"
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
