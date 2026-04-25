from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path

import httpx
from pdf2image import convert_from_path
from PIL import Image

from science_graphrag.config import Settings
from science_graphrag.observability.phoenix_tracer import SpanAttributes, llm_span

DEFAULT_VL_PROMPT = (
    "Extract the document text faithfully as Markdown. "
    "Preserve headings, paragraphs, lists, tables where possible, authors, affiliations, "
    "references, and URLs. Output only the document content in Markdown."
)


class VLPDFProcessor:
    """Minimal OpenRouter-compatible VL PDF-to-Markdown processor."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

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

    def pdf_to_markdown(self, path: Path) -> str:
        if not self.settings.vl_api_key:
            raise ValueError("VL API key is not configured")

        with llm_span(
            "llm.vl_pdf",
            {
                "vl.model": self.settings.vl_model,
                "vl.base_url": self.settings.vl_base_url,
                "pdf.path": str(path),
            },
        ):
            images = self._pdf_pages(path)
            if not images:
                raise ValueError("No pages available for VL processing")

            content: list[dict[str, object]] = []
            for img in images:
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": self._image_to_data_url(img)},
                    }
                )
            content.append({"type": "text", "text": DEFAULT_VL_PROMPT})

            headers = {
                "Authorization": f"Bearer {self.settings.vl_api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.settings.vl_model,
                "messages": [{"role": "user", "content": content}],
                "temperature": 0.0,
                "max_tokens": 12000,
            }

            with httpx.Client(timeout=300.0) as client:
                response = client.post(
                    f"{self.settings.vl_base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
            markdown = data["choices"][0]["message"]["content"]
            SpanAttributes.set_llm_attrs(
                model=self.settings.vl_model,
                base_url=self.settings.vl_base_url,
                temperature=0.0,
                max_tokens=12000,
            )
            SpanAttributes.set_llm_invocation_parameters(
                {
                    "max_tokens": 12000,
                    "pages": len(images),
                    "dpi": self.settings.vl_dpi,
                }
            )
            SpanAttributes.set_llm_input_messages(
                [{"role": "user", "content": f"<{len(images)} image(s)> + VL prompt"}]
            )
            SpanAttributes.set_llm_output_messages([{"role": "assistant", "content": markdown}])
            usage = data.get("usage")
            if isinstance(usage, dict):
                prompt_tokens = usage.get("prompt_tokens")
                completion_tokens = usage.get("completion_tokens")
                total_tokens = usage.get("total_tokens")
                if prompt_tokens is not None or completion_tokens is not None:
                    SpanAttributes.set_llm_token_counts(
                        prompt_tokens=int(prompt_tokens) if prompt_tokens is not None else None,
                        completion_tokens=(
                            int(completion_tokens) if completion_tokens is not None else None
                        ),
                        total_tokens=int(total_tokens) if total_tokens is not None else None,
                        usage_source="api",
                    )
                else:
                    SpanAttributes.set_llm_token_counts_from_text(
                        prompt_text=DEFAULT_VL_PROMPT,
                        completion_text=markdown,
                    )
            else:
                SpanAttributes.set_llm_token_counts_from_text(
                    prompt_text=DEFAULT_VL_PROMPT,
                    completion_text=markdown,
                )
            return markdown
