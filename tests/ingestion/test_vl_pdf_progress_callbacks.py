"""VL PDF progress callback ordering (no network)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from science_graphrag.ingestion.vl_pdf import VLPDFProcessor


def test_pdf_to_markdown_batches_ready_and_page_progress_order() -> None:
    """VL invokes batch layout callback then page progress before/after each HTTP batch."""
    settings = MagicMock()
    settings.vl_api_key = "test-key"
    settings.vl_dpi = 72
    settings.vl_max_pages = 0
    settings.vl_batch_size = 1
    settings.vl_model = "m"
    settings.vl_base_url = "http://example"
    settings.vl_max_tokens = 100

    proc = VLPDFProcessor(settings)
    fake_pages = [MagicMock(name=f"p{i}") for i in range(2)]

    events: list[tuple] = []

    def on_ready(bc: int, pc: int, bs: int) -> None:
        events.append(("ready", bc, pc, bs))

    def on_prog(done: int, tot: int) -> None:
        events.append(("prog", done, tot))

    with patch.object(proc, "_pdf_pages", return_value=fake_pages):
        with patch.object(proc, "_call_vl_api", return_value=("part", {"prompt_tokens": 0})):
            out = proc.pdf_to_markdown(
                Path("dummy.pdf"),
                on_page_progress=on_prog,
                on_batches_ready=on_ready,
            )

    assert "part" in out
    assert events[0] == ("ready", 2, 2, 1)
    assert events[1] == ("prog", 0, 2)
    assert events[2] == ("prog", 1, 2)
    assert events[3] == ("prog", 1, 2)
    assert events[4] == ("prog", 2, 2)
