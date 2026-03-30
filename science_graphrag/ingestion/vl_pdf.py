from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path

import httpx
from pdf2image import convert_from_path
from PIL import Image

from science_graphrag.config import Settings
from science_graphrag.observability.phoenix_tracer import llm_span

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
            "vl_pdf.chat_completions",
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
            return data["choices"][0]["message"]["content"]
