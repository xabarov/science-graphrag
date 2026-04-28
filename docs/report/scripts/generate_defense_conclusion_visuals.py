#!/usr/bin/env python3
"""Generate static PNG visuals for defense deck conclusion slides (10–12).

Run from repo root or any CWD:
  .venv/bin/python docs/report/scripts/generate_defense_conclusion_visuals.py

Outputs:
  docs/report/assets/defense/slide-10-benchmark-conclusions.png
  docs/report/assets/defense/slide-11-agent-tracing-ui.png
  docs/report/assets/defense/slide-12-plans-roadmap.png
"""

from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = Path(__file__).resolve().parent
ASSETS_DEFENSE = SCRIPT_DIR.parent / "assets" / "defense"

W, H = 1600, 900
# Match deck: warm paper + ink
BG = (248, 244, 236)
INK = (34, 40, 48)
INK_SOFT = (90, 96, 108)
ACCENT = (99, 102, 141)
ACCENT_SOFT = (180, 184, 210)
WARN = (180, 120, 70)
OK = (70, 130, 95)


def _try_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _save(img: Image.Image, name: str) -> Path:
    ASSETS_DEFENSE.mkdir(parents=True, exist_ok=True)
    path = ASSETS_DEFENSE / name
    img.save(path, format="PNG", optimize=True)
    return path


def draw_benchmark_conclusions() -> None:
    """Intersection / threshold metaphor + noisy reference strip."""
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    font_title = _try_font(34)
    font_small = _try_font(22)

    d.text((60, 48), "Benchmarks → metrics, not binary ticks", fill=INK, font=font_title)

    # Two overlapping circles (Venn)
    cx, cy = 420, 480
    r = 180
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=ACCENT, width=5)
    d.ellipse((cx + 80 - r, cy - r, cx + 80 + r, cy + r), outline=ACCENT_SOFT, width=5)
    d.text((cx - 40, cy + r + 36), "overlap / thresholds", fill=INK_SOFT, font=font_small)

    # Bar with partial match (not 0/1)
    bx, by, bw, bh = 780, 360, 720, 36
    for i in range(20):
        fill = OK if i < 14 else WARN if i < 18 else (200, 200, 200)
        d.rectangle((bx + i * (bw // 20), by, bx + (i + 1) * (bw // 20), by + bh), fill=fill)
    d.rectangle((bx, by, bx + bw, by + bh), outline=INK, width=2)
    d.text((bx, by - 40), "field score distribution (illustrative)", fill=INK_SOFT, font=font_small)

    # Noisy reference lines (literature layer)
    y0 = 620
    for i in range(8):
        y = y0 + i * 28
        jitter = (i % 3) * 6
        d.line((bx + jitter, y, bx + bw - 40 + jitter, y), fill=INK_SOFT, width=2)
    d.text((bx, y0 - 36), "references: noisy PDF layer", fill=INK_SOFT, font=font_small)

    _save(img, "slide-10-benchmark-conclusions.png")


def _draw_dense_graph_sketch(
    draw: ImageDraw.ImageDraw,
    origin_x: int,
    origin_y: int,
    caption_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    """Random-ish edges + nodes to suggest a heavy browser graph."""
    random.seed(42)
    pts = [
        (origin_x + random.randint(0, 200), origin_y + random.randint(0, 140)) for _ in range(14)
    ]
    for _ in range(22):
        a, b = random.sample(pts, 2)
        draw.line((*a, *b), fill=INK_SOFT, width=1)
    for px, py in pts:
        draw.ellipse(
            (px - 5, py - 5, px + 5, py + 5),
            fill=ACCENT_SOFT,
            outline=INK,
        )
    draw.text(
        (origin_x, origin_y - 36),
        "large graph render: density vs readability",
        fill=INK_SOFT,
        font=caption_font,
    )


def draw_agent_tracing_ui() -> None:
    """Step chain + trace timeline + graph sketch."""
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    font_title = _try_font(34)
    font_small = _try_font(20)

    d.text((60, 48), "Agent path → traceable steps", fill=INK, font=font_title)

    # Nodes along a path
    nodes = [(120, 420), (320, 320), (520, 400), (720, 280), (920, 360), (1120, 300)]
    for (x1, y1), (x2, y2) in zip(nodes, nodes[1:]):
        d.line((x1, y1, x2, y2), fill=ACCENT, width=4)
    last_i = len(nodes) - 1
    for i, (x, y) in enumerate(nodes):
        node_fill = ACCENT if i < last_i else WARN
        d.ellipse(
            (x - 18, y - 18, x + 18, y + 18),
            fill=node_fill,
            outline=INK,
            width=2,
        )
    d.text((120, 500), "tool calls", fill=INK_SOFT, font=font_small)

    # Vertical trace ticks
    tx = 1280
    for i in range(12):
        y = 200 + i * 52
        hue = ACCENT if i not in (5, 9) else WARN
        d.line((tx, y, tx + 40, y), fill=hue, width=3)
        d.ellipse((tx + 50, y - 6, tx + 62, y + 6), fill=hue)
    d.text((tx, 160), "UI event stream", fill=INK_SOFT, font=font_small)

    _draw_dense_graph_sketch(d, 200, 620, font_small)

    _save(img, "slide-11-agent-tracing-ui.png")


def draw_plans_roadmap() -> None:
    """Horizontal roadmap + expansion."""
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    font_title = _try_font(34)
    font_small = _try_font(22)

    title = "Roadmap: tool search → context → precision → scale"
    d.text((60, 48), title, fill=INK, font=font_title)

    steps = [
        ("tool\nsearch", 140),
        ("context\ncompaction", 420),
        ("claims /\ngraph precision", 700),
        ("corpus +\ngraph UI", 1020),
    ]
    y = 400
    white = (255, 255, 255)
    for i, (label, x) in enumerate(steps):
        box = (x, y - 80, x + 220, y + 80)
        d.rounded_rectangle(box, radius=12, outline=ACCENT, width=4, fill=white)
        d.multiline_text((x + 24, y - 50), label, fill=INK, font=font_small, spacing=4)
        if i < len(steps) - 1:
            _, nx = steps[i + 1]
            d.line((x + 220, y, nx, y), fill=ACCENT, width=4)
            d.polygon([(nx - 18, y - 12), (nx, y), (nx - 18, y + 12)], fill=ACCENT)

    d.rounded_rectangle(
        (100, 640, 1500, 820),
        radius=10,
        outline=INK_SOFT,
        width=2,
        fill=white,
    )
    d.text((130, 680), "ship honest metrics + traces each release", fill=INK_SOFT, font=font_small)

    _save(img, "slide-12-plans-roadmap.png")


def main() -> None:
    """Render all conclusion visuals into docs/report/assets/defense/."""
    draw_benchmark_conclusions()
    draw_agent_tracing_ui()
    draw_plans_roadmap()
    print("Wrote:", ASSETS_DEFENSE / "slide-10-benchmark-conclusions.png")
    print("Wrote:", ASSETS_DEFENSE / "slide-11-agent-tracing-ui.png")
    print("Wrote:", ASSETS_DEFENSE / "slide-12-plans-roadmap.png")


if __name__ == "__main__":
    main()
