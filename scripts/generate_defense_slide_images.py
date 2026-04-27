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

    return [
        ImageJob(
            slug="slide-02-plan-motif",
            filename_base="slide-02-plan-motif",
            prompt=(
                """
Create a minimal 16:9 academic motif image for a thesis defense slide about GraphRAG.

The image should be decorative and thematic, not explanatory and not text-heavy.
No slide title inside the image.
No labels if possible.
No fake UI.
No fake charts.
No readable paragraphs.

Use a calm editorial composition:
- a few paper/document cards
- a compact graph / node-link cluster
- subtle directional flow toward a small answer card
- maybe a small citation hint or grounded-answer cue

The image should feel elegant, spacious, quiet, and abstract.
It should suggest GraphRAG, retrieval, knowledge graph, and grounded answers without looking like a dashboard or a tutorial diagram.
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
Create a high-end architecture diagram for a GraphRAG scientific research system, designed for a thesis defense slide in 16:9 format.

Show two separate phases of the system, not one continuous pipeline.

Phase 1: offline ingest
documents (PDF / Markdown / Text) ->
normalization into article markdown ->
LLM extraction pipeline ->
three storage systems (PostgreSQL, Neo4j, Qdrant).

Phase 2: online chat runtime
user query ->
supervisor / orchestrator ->
three specialized agents (retrieval agent, graph agent, writer agent) ->
read from PostgreSQL, Neo4j, Qdrant ->
final answer with citations.

Emphasize that:
- ingestion happens offline before chat
- chat runtime does not perform ingestion
- the specialized agents do not communicate directly with each other
- there must be no direct arrows between retrieval agent, graph agent, and writer agent
- all routing goes through the supervisor only

If the diagram contains labels, keep them very short and preferably in English.
Examples of acceptable labels:
Input, Normalize, Extract, Postgres, Neo4j, Qdrant, Supervisor, Retrieval, Graph, Writer, Citations.
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
    jobs = build_jobs()
    if selected:
        jobs = [job for job in jobs if job.slug in selected]
        if not jobs:
            print(f"No jobs matched --only={sorted(selected)}", file=sys.stderr)
            return 2

    out_dir = (repo_root / args.out_dir).resolve()
    ensure_directory(out_dir)
    write_manifest(out_dir, jobs, MODEL_NAME)

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
