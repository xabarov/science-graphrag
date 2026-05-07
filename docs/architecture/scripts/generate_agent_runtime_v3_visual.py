#!/usr/bin/env python3
"""Generate a PNG visual for SciGraph agent runtime v3 architecture.

Run from repo root (or any CWD):
  .venv/bin/python docs/architecture/scripts/generate_agent_runtime_v3_visual.py

Output:
  docs/readme-assets/agent-runtime-v3-architecture.png
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent
OUTPUT_PATH = REPO_ROOT / "docs" / "readme-assets" / "agent-runtime-v3-architecture.png"

W, H = 1800, 1040

BG = (14, 20, 34)
CARD = (30, 40, 62)
CARD_ALT = (34, 51, 72)
INK = (236, 241, 255)
INK_SOFT = (179, 193, 224)
ACCENT = (116, 146, 255)
ACCENT_2 = (95, 214, 255)
GOOD = (92, 173, 120)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
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


def _rounded(
    d: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    fill: tuple[int, int, int],
    outline: tuple[int, int, int],
    width: int = 2,
    radius: int = 18,
) -> None:
    d.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def _arrow(
    d: ImageDraw.ImageDraw,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    color: tuple[int, int, int],
    width: int = 4,
) -> None:
    d.line((x1, y1, x2, y2), fill=color, width=width)
    if x2 >= x1:
        tri = [(x2, y2), (x2 - 18, y2 - 11), (x2 - 18, y2 + 11)]
    else:
        tri = [(x2, y2), (x2 + 18, y2 - 11), (x2 + 18, y2 + 11)]
    d.polygon(tri, fill=color)


def main() -> None:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    f_title = _font(44)
    f_h2 = _font(27)
    f_text = _font(22)
    f_small = _font(18)

    d.text((60, 42), "SciGraph Agent Runtime v3 Architecture", fill=INK, font=f_title)
    d.text(
        (60, 95),
        "Single endpoint, structured lifecycle, typed merge, and fork-first child work.",
        fill=INK_SOFT,
        font=f_text,
    )

    # Top API strip
    _rounded(d, (60, 150, 1740, 245), fill=(21, 31, 51), outline=(64, 85, 130))
    d.text((90, 184), "POST /v2/agent/query", fill=ACCENT_2, font=f_h2)
    d.text(
        (455, 188),
        "Canonical API stays stable while runtime moves to v3 contracts.",
        fill=INK,
        font=f_text,
    )

    # Core v3 boxes
    _rounded(d, (90, 320, 500, 560), fill=CARD, outline=(79, 101, 150))
    d.text((120, 355), "Policy + Prompt Build", fill=INK, font=f_h2)
    d.text((120, 402), "- turn_policy", fill=INK_SOFT, font=f_text)
    d.text((120, 437), "- tool_search shortlist", fill=INK_SOFT, font=f_text)
    d.text((120, 472), "- memory ladder L1..L4", fill=INK_SOFT, font=f_text)

    _rounded(d, (585, 320, 1010, 560), fill=CARD_ALT, outline=(87, 121, 162))
    d.text((615, 355), "Supervisor v3 Runtime", fill=INK, font=f_h2)
    d.text((615, 402), "- parent_turn_id", fill=INK_SOFT, font=f_text)
    d.text((615, 437), "- specialist routing legs", fill=INK_SOFT, font=f_text)
    d.text((615, 472), "- heartbeat / progress labels", fill=INK_SOFT, font=f_text)

    _rounded(d, (1095, 320, 1710, 560), fill=CARD, outline=(105, 121, 183), width=3)
    d.text((1125, 355), "Subagent Lifecycle + Merge", fill=INK, font=f_h2)
    d.text((1125, 402), "- subagent_runs", fill=INK_SOFT, font=f_text)
    d.text((1125, 437), "- task notifications", fill=INK_SOFT, font=f_text)
    d.text((1125, 472), "- specialist_results_v3", fill=INK_SOFT, font=f_text)

    _arrow(d, 500, 440, 585, 440, ACCENT)
    _arrow(d, 1010, 440, 1095, 440, ACCENT)

    # Bottom lane
    _rounded(d, (90, 650, 1710, 940), fill=(21, 31, 51), outline=(64, 85, 130))
    d.text((120, 685), "Fork-first child work (baseline)", fill=GOOD, font=f_h2)
    d.text(
        (120, 730),
        "cache-safe side LLM pattern: keep shared prefix stable, isolate child transcript, carry back structured result.",
        fill=INK_SOFT,
        font=f_text,
    )
    d.text((120, 785), "Examples: claim_verification, future corpus-explore, research-plan.", fill=INK_SOFT, font=f_text)
    d.text((120, 840), "Coordinator mode is optional and only for explicit user-visible specialist continuation.", fill=INK_SOFT, font=f_text)

    d.text(
        (120, 895),
        "Observed in output: run_kind=supervisor_specialists_v3, graph_id=supervisor_graph_v3, richer run_metadata.",
        fill=ACCENT_2,
        font=f_small,
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUTPUT_PATH, format="PNG", optimize=True)
    print(f"Wrote: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
