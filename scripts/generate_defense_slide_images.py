"""
Генерация визуалов для защиты NLP Advanced через OpenRouter image model.

Основано на /home/roman/pyprojects/work/calc_safe_distances/scripts/openrouter_image_client.py,
но адаптировано под пакетную генерацию слайдов защиты и модель
google/gemini-3.1-flash-image-preview.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import requests


MODEL_NAME = "google/gemini-3.1-flash-image-preview"
DEFAULT_HTTP_REFERER = "http://localhost/science-graphrag-defense"
DEFAULT_X_TITLE = "science-graphrag-defense-images"


@dataclass(frozen=True)
class ImageJob:
    slug: str
    filename_base: str
    prompt: str


def load_dotenv_if_available(dotenv_path: Path) -> None:
    """Пытается загрузить .env через python-dotenv; если пакета нет — читает файл вручную."""
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv(dotenv_path)
        return
    except ModuleNotFoundError:
        pass

    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def collect_images_from_chat_response(data: Dict[str, Any]) -> List[str]:
    """Извлекает data-URL или base64 payload из ответа chat/completions."""
    images: List[str] = []
    for choice in data.get("choices", []):
        msg = choice.get("message", {})
        for img_url in msg.get("images", []):
            if isinstance(img_url, dict):
                url = img_url.get("image_url", {}).get("url", "") or img_url.get("url", "")
                if url:
                    images.append(url)
                    continue
            if isinstance(img_url, str):
                images.append(img_url)
        content = msg.get("content", "")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "image_url":
                    url = block.get("image_url", {}).get("url", "")
                    if url:
                        images.append(url)
    return images


def decode_first_image_payload(img_data_url: str | Dict[str, Any]) -> Tuple[bytes, str]:
    """Декодирует изображение и возвращает байты + расширение файла."""
    if isinstance(img_data_url, dict):
        if img_data_url.get("type") == "image_url":
            img_data_url = img_data_url.get("image_url", {}).get("url", "") or ""
        else:
            img_data_url = img_data_url.get("url") or img_data_url.get("b64_json") or ""

    if isinstance(img_data_url, dict):
        raise ValueError("Unexpected nested image payload")

    ext = ".png"
    if img_data_url.startswith("data:"):
        header, b64 = img_data_url.split(",", 1)
        if ";base64" in header:
            mime = header[5:].split(";", 1)[0].strip().lower()
            ext = {
                "image/png": ".png",
                "image/jpeg": ".jpg",
                "image/jpg": ".jpg",
                "image/webp": ".webp",
            }.get(mime, ".png")
    else:
        b64 = img_data_url

    return base64.b64decode(b64), ext


def post_openrouter_image(
    *,
    prompt: str,
    http_referer: str,
    x_title: str,
    timeout_sec: int = 180,
    max_attempts: int = 3,
    model_override: str | None = None,
) -> Tuple[bytes, str]:
    """Отправляет prompt в OpenRouter и возвращает байты первого изображения + расширение."""
    api_key = (
        os.getenv("OPENROUTER_API_KEY")
        or os.getenv("SCIENCE_GRAPHRAG_VL_API_KEY")
        or os.getenv("SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY")
    )
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    model = model_override or MODEL_NAME

    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY не найден в окружении / .env")

    last_error: str | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": http_referer,
                    "X-Title": x_title,
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "modalities": ["image", "text"],
                },
                timeout=timeout_sec,
            )

            if response.status_code != 200:
                raise RuntimeError(f"HTTP {response.status_code}: {response.text}")

            try:
                data = response.json()
            except requests.exceptions.JSONDecodeError as exc:
                snippet = response.text[:500]
                raise RuntimeError(
                    "OpenRouter вернул невалидный JSON "
                    f"(attempt {attempt}/{max_attempts}): {exc}. "
                    f"Body snippet: {snippet!r}"
                ) from exc

            images = collect_images_from_chat_response(data)
            if not images:
                raise RuntimeError(
                    "Изображение не найдено в ответе:\n"
                    f"{json.dumps(data, ensure_ascii=False, indent=2)}"
                )

            return decode_first_image_payload(images[0])
        except (requests.RequestException, RuntimeError, ValueError) as exc:
            last_error = str(exc)
            if attempt == max_attempts:
                break
            time.sleep(min(2 * attempt, 6))

    raise RuntimeError(last_error or "Неизвестная ошибка OpenRouter image request")


def build_jobs() -> List[ImageJob]:
    base_suffix = """

Create a clean academic presentation visual for a master's-level NLP / GraphRAG defense.
Style: editorial, premium, minimal, research-oriented, light background, subtle paper texture, thin dividers, soft shadows, strong information hierarchy.
Palette: warm off-white background, dark graphite text, muted terracotta accent, cool gray-blue secondary accent.
Avoid text-heavy visuals. Do not place the slide title inside the image.
If labels are necessary, keep them extremely short and prefer simple English words or short technical terms, not sentences.
Avoid neon gradients, futuristic holograms, generic AI dashboard aesthetics, glossy 3D objects, clutter, and fake startup visuals.
""".strip()

    # Last slides: intentionally more saturated and illustrative than ``base_suffix`` (still no text).
    vibrant_no_text_suffix = """

16:9 presentation art for a technical thesis defense. Mood: confident, warm, lively — NOT washed-out gray, NOT a thin wireframe schematic, NOT a fake dashboard.

Use rich but tasteful color: deep teal, coral/amber, soft violet accents, warm ivory/cream base, clear focal lighting and depth (volumetric glow, soft vignette, layered planes).

Hard constraints:
- Absolutely NO readable text: no letters, words, numbers, axis labels, metric names, logos, or UI strings anywhere in the image.
- No bar charts pretending to show data, no fake precision/recall numbers.
- Avoid flat all-pastel mush; keep strong hue contrast and at least one vivid accent area.

The image must work as a decorative hero next to real HTML slide text (text lives outside the image).
""".strip()

    return [
        ImageJob(
            slug="slide-02-plan-motif",
            filename_base="slide-02-plan-motif",
            prompt=(
                """
Create a striking 16:9 hero illustration for a thesis defense slide titled "defense plan" — it must feel memorable and premium, not like a thin wireframe tutorial.

Concept to convey (visually, not as a labeled diagram): scientific papers -> knowledge graph -> retrieval path -> grounded answer with citations.

Make it interesting through art direction, not through more text:
- strong focal lighting and depth (soft vignette, gentle spotlight, layered paper planes)
- one bold graph motif as the centerpiece: fewer nodes but larger, sculptural, with confident edges and warm terracotta + cool slate accents
- implied motion: papers drifting into the graph, a luminous trail toward an answer card or parchment strip with tiny citation markers (ticks or brackets), not a fake app screenshot
- subtle texture: deckle edges, grain, or print-like noise at low opacity
- asymmetry and overlap: staggered cards, partial crops, overlapping shapes so the frame feels designed, not empty

Hard constraints:
- no slide title inside the image
- no readable paragraphs, no dashboard UI, no fake metrics, no neon sci-fi
- if any micro-labels appear, at most 3-4 tiny English words total (optional); prefer zero text

Avoid a flat schematic clipart look: do not use ultra-thin uniform connector lines across the whole canvas like a textbook diagram.
"""
                + "\n\n"
                + base_suffix
            ).strip(),
        ),
        ImageJob(
            slug="slide-03-goal-visual",
            filename_base="slide-03-goal-visual",
            prompt=(
                """
Create a bold, visually dominant 16:9 academic illustration for a thesis defense slide about the goal and tasks of a scientific GraphRAG system.

The composition should read left-to-right as a clear story:
papers / corpus -> knowledge graph (node-link cluster) -> retrieval / query path -> compact answer card with citation markers.

Make the graph and flow the main focal point. Use large shapes, strong hierarchy, and generous negative space, but avoid empty canvas feeling by filling the frame with meaningful structure.

Constraints:
- no slide title inside the image
- minimal text, preferably no text at all
- if any labels are needed, use at most a few tiny English words like Papers, Graph, Query, Answer, Citations
- no fake numbers, no fake charts, no fake UI screenshots
- no neon, no glossy 3D, no startup dashboard look

The image should feel premium, editorial, and abstract, but still clearly about GraphRAG and grounded scientific answers.
"""
                + "\n\n"
                + base_suffix
            ).strip(),
        ),
        ImageJob(
            slug="slide-04-tech-stack",
            filename_base="slide-04-tech-stack",
            prompt=(
                """
Create a very clean 16:9 academic infographic for a GraphRAG technology stack slide.

Use exactly 5 sections only:
Backend, Storage, NLP Pipeline, UI / Observability, Evaluation.

No duplicates.
No repeated labels.
No slide title inside the image.
Very little text.
Only short English labels.
No Russian text.
No decorative fake charts.
No repeated metric names.
No tiny labels.
No dense lists.
Keep the composition simpler than a dashboard.

Stack:
- Backend: Python, FastAPI, orchestration / supervisor
- Storage: PostgreSQL, Neo4j, Qdrant
- NLP Pipeline: extraction, embeddings, retrieval, graph query, answer generation
- UI / Observability: React UI, traces, logs, metrics
- Evaluation: show only a very small and clean symbolic metrics area using no more than 3-4 short metric labels chosen from P / R / F1, ROUGE-L, latency_p95, recall, precision, ARI, hit_count, forbidden_violation_count

Make the result feel like a polished systems overview, not a KPI board.
Prefer icons, blocks, and separators over text.
Do not use long labels such as Forbidden_Violation_Count as visible text unless they are heavily simplified.
Do not show metric values or invented numbers.
Do not display fake latency values, fake precision/recall numbers, or fake dashboard counters.
"""
                + "\n\n"
                + base_suffix
            ).strip(),
        ),
        ImageJob(
            slug="slide-05-architecture",
            filename_base="slide-05-architecture",
            prompt=(
                """
Create a high-end architecture diagram for a GraphRAG scientific research system, thesis defense slide, 16:9.

Two phases only — visually separated (e.g. horizontal band split or two stacked panels).

Phase 1 title text (short English): "PHASE 1: INGESTION (OFFLINE)"
Flow left to right:
Input (PDF / MD / TXT) -> Normalize -> Article Markdown -> Extract (LLM pipeline) ->
three stores under a small "STORAGE LAYER" label: PostgreSQL (metadata), Neo4j (structure), Qdrant (embeddings).

Phase 2 title text (short English): "PHASE 2: AGENT RUNTIME (ONLINE)" — NOT "RAG RUNTIME".

Phase 2 must show a **single** central box labeled "RESEARCH AGENT (ReAct + tools)" (or "AGENT + TOOLS").
User query arrow enters this single agent.

From that ONE agent, show **multiple small tool chips or a compact "TOOLS" strip** (not separate agent personas):
examples of tiny labels: catalog, find_works, quotes, graph query, bibliography, final_answer.
Arrows from the agent/tools area **down** to the same three stores (Postgres, Neo4j, Qdrant) — read/write semantics implied as read-mostly.

Then arrow to a final box "ANSWER WITH CITATIONS".

Critical constraints:
- Do **NOT** draw a supervisor orchestrator.
- Do **NOT** draw three separate specialist agents (no Retrieval Agent / Graph Agent / Writer Agent as three peer boxes).
- Do **NOT** add arrows between hypothetical sub-agents — there is only one agent node.
- Ingest is offline only; runtime does not re-ingest.

Labels: short English only; no Russian; no slide title inside the image; no fake metrics.
"""
                + "\n\n"
                + base_suffix
            ).strip(),
        ),
        ImageJob(
            slug="slide-06-product-collage",
            filename_base="slide-06-product-collage",
            prompt=(
                """
Create a clean abstract supporting visual for a scientific software project presentation.

This image should suggest:
- a research interface
- a graph / knowledge structure
- implementation modules
- evaluation artifacts

But it must NOT contain fake readable code, fake dashboards, fake charts with detailed numbers, or fake product screenshots pretending to be real.

Use a modular editorial composition with 3-4 large visual zones, subtle cards, graph motifs, interface silhouettes, and software architecture hints.
The result should feel serious, minimal, and academic, not like an AI-generated product mockup.

Important constraints:
- no fake code blocks with readable text
- no fake analytics dashboard
- no dense labels
- no slide title inside the image
- if captions are added, use at most a few tiny generic words
- prefer shapes, panes, graph nodes, connectors, and UI silhouettes over text
- avoid the look of a full screenshot

The image should work as a background/supporting visual next to real HTML text, not as the main source of factual content.
"""
                + "\n\n"
                + base_suffix
            ).strip(),
        ),
        ImageJob(
            slug="slide-07-metrics",
            filename_base="slide-07-metrics",
            prompt=(
                """
Create a refined academic metrics visual for a GraphRAG thesis defense slide.

The image should communicate four result dimensions:
1) structured extraction quality
2) graph citation quality
3) retrieval effectiveness
4) end-to-end agent performance

Prefer fewer labels and more visual structure.
If text is needed, keep it short and preferably in English.
Do not use invented or irrelevant metrics.

Good metric examples:
- Methods: P / R / F1 = 0.617 / 0.680 / 0.601
- Datasets: P / R / F1 = 0.790 / 0.879 / 0.792
- Graph CITES (Neo4j): P / R / F1 = 0.784 / 0.909 / 0.821
- workspace_scoped_live: forbidden_violation_count = 0
- hybrid_ablation_live: hit_count = 5/5
- multihop_v2: recall ≈ 0.667, precision low
- claims_paraphrase: macro P / R / F1
- agent_tools_live: latency_p95 = 25 983 ms, judge = 4.8/6
"""
                + "\n\n"
                + base_suffix
            ).strip(),
        ),
        ImageJob(
            slug="slide-08-demo-poster",
            filename_base="slide-08-demo-poster",
            prompt=(
                """
Create a clean poster-style presentation visual for a GraphRAG system demo slide.
The image should suggest a live scientific question-answering workflow with citations, graph reasoning, and retrieval over papers.
Use a premium academic style, light background, restrained editorial composition, subtle interface hints, and clear focal hierarchy.
No fake futuristic AI assistant face, no neon holograms, no sci-fi clichés.
Do not put the slide title inside the image.
If there is any caption text, keep it minimal.
"""
                + "\n\n"
                + base_suffix
            ).strip(),
        ),
        ImageJob(
            slug="slide-10-benchmark-conclusions",
            filename_base="slide-10-benchmark-conclusions",
            prompt=(
                """
Create a bold, painterly-edged 16:9 illustration for a "Conclusions" slide about scientific PDF pipelines,
benchmarks, evaluation, and honest metrics — convey the IDEA only through abstract composition.

Suggested visual language (pick what fits best, merge creatively):
- stacked translucent layers or paper decks suggesting PDFs / manuscripts transforming into structured flow
- two or three overlapping translucent disks or lenses suggesting set overlap, thresholds, and fuzzy matching (NOT labeled)
- a luminous "pipeline" ribbon or channel moving left-to-right with glowing particles (data in motion), ending in a calm focal glow (grounded output) — still abstract, not a UI
- subtle graph motif: a few large nodes with thick confident edges in saturated teal and coral (few nodes, not a hairball)

The piece should feel optimistic and rigorous: "we measure carefully" without showing any metrics as text.
"""
                + "\n\n"
                + vibrant_no_text_suffix
            ).strip(),
        ),
        ImageJob(
            slug="slide-12-plans-roadmap",
            filename_base="slide-12-plans-roadmap",
            prompt=(
                """
Create an uplifting 16:9 illustration for a final "Roadmap / future work" slide about scaling a GraphRAG research system:
multi-agent tooling, long-context handling, evaluation discipline, graph engine feel, ingestion pipelines, deduplication — all as pure visual metaphor (no text).

Suggested metaphors (no text):
- an ascending path: stepping stones, bridge, or rising terraces moving upward into brighter light (sunrise / horizon glow)
- a growing network: glowing nodes and bold curved links suggesting a knowledge graph expanding with energy
- subtle parallel "lanes" or layered ribbons suggesting pipeline + agent runtime + product track merging upward
- depth cues: foreground rocks or paper planes, midground bridge/path, background sky with warm gradient (amber to teal)

Convey forward momentum and "shipping" energy without clocks, Gantt charts, arrows with labels, or roadmap words.
Keep the composition asymmetric and interesting; avoid a bland 4-box flowchart silhouette.
"""
                + "\n\n"
                + vibrant_no_text_suffix
            ).strip(),
        ),
    ]


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_manifest(out_dir: Path, jobs: Iterable[ImageJob], model_name: str) -> None:
    manifest = {
        "model": model_name,
        "generated_at_epoch": int(time.time()),
        "jobs": [{"slug": job.slug, "filename_base": job.filename_base} for job in jobs],
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate defense slide images via OpenRouter.")
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="Generate only matching slug(s); can be provided multiple times.",
    )
    parser.add_argument(
        "--out-dir",
        default="docs/report/assets/defense",
        help="Output directory relative to repo root.",
    )
    parser.add_argument(
        "--timeout-sec",
        type=int,
        default=180,
        help="Per-request timeout in seconds.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    dotenv_path = repo_root / ".env"
    load_dotenv_if_available(dotenv_path)

    selected = set(args.only or [])
    all_jobs = build_jobs()
    jobs = all_jobs
    if selected:
        jobs = [job for job in all_jobs if job.slug in selected]
        if not jobs:
            print(f"No jobs matched --only={sorted(selected)}", file=sys.stderr)
            return 2

    out_dir = (repo_root / args.out_dir).resolve()
    ensure_directory(out_dir)
    # Always record the full job catalog (partial runs with --only should not shrink manifest).
    write_manifest(out_dir, all_jobs, MODEL_NAME)

    failures: List[Tuple[str, str]] = []
    for index, job in enumerate(jobs, start=1):
        print(f"[{index}/{len(jobs)}] Generating {job.slug} with {MODEL_NAME}...")
        try:
            image_bytes, ext = post_openrouter_image(
                prompt=job.prompt,
                http_referer=DEFAULT_HTTP_REFERER,
                x_title=DEFAULT_X_TITLE,
                timeout_sec=args.timeout_sec,
                model_override=MODEL_NAME,
            )
            out_path = out_dir / f"{job.filename_base}{ext}"
            out_path.write_bytes(image_bytes)
            print(f"  saved -> {out_path}")
        except Exception as exc:  # noqa: BLE001
            failures.append((job.slug, str(exc)))
            print(f"  FAILED -> {job.slug}: {exc}", file=sys.stderr)

    if failures:
        print("\nGeneration completed with failures:", file=sys.stderr)
        for slug, error in failures:
            print(f"- {slug}: {error}", file=sys.stderr)
        return 1

    print(f"\nAll {len(jobs)} image(s) generated successfully in {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
