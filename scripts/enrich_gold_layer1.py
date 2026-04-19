#!/usr/bin/env python3
"""
Enrich layer-1 benchmark ``gold.json`` from ``article.md`` + ``references_benchmark.raw_entries``.

Step A (free): regex arXiv ids from ``references_benchmark.raw_entries`` (aligned with layer-1).
Step B (LLM): year, work ``arxiv_id``/``doi``, ``authorships`` from start of ``article.md``.

Writes ``gold_enrichment_<case_id>.json`` beside ``gold.json``.
``--apply`` merges into ``gold.json`` (validated with ``Layer1GoldSpec``).

Environment: ``TESTGEN_LLM_API_KEY``, ``TESTGEN_LLM_BASE_URL``, ``TESTGEN_LLM_MODEL``
(OpenAI-compatible chat-completions).
Optional ``--env-file`` loads KEY=value (secrets are never printed).

Examples::
  .venv/bin/python scripts/enrich_gold_layer1.py --cases faster_rcnn_realpdf detr_realpdf yolov1 \\
    --dry-run
  .venv/bin/python scripts/enrich_gold_layer1.py --all-nightly --dry-run
  .venv/bin/python scripts/enrich_gold_layer1.py --cases faster_rcnn_realpdf --apply
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.layer1.spec import Layer1GoldSpec  # noqa: E402

FIXTURE_LAYER1 = ROOT / "tests" / "fixtures" / "benchmarks" / "layer1"

# Match arXiv ids in bibliography text (aligned with eval/layer1/metrics.py heuristics).
_ARXIV_IN_TEXT_RE = re.compile(
    r"(?:arxiv:\s*)?(\d{4}\.\d{4,5})(?:v\d+)?\b|abs/(\d{4}\.\d{4,5})(?:v\d+)?\b",
    re.IGNORECASE,
)

DEFAULT_HEADER_LINES = 120
DEFAULT_MIN_AUTHORSHIP_NAMES_F1 = 0.7
DEFAULT_MIN_SAMPLE_ARXIV_F1 = 0.7


def _load_dotenv_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def collect_arxiv_ids_from_text(text: str) -> list[str]:
    """Return sorted unique arXiv ids (``YYMM.NNNNN``) found in ``text``."""
    found: set[str] = set()
    for m in _ARXIV_IN_TEXT_RE.finditer(text):
        aid = m.group(1) or m.group(2)
        if aid:
            found.add(aid.strip())
    return sorted(found)


def step_a_from_gold(gold: dict[str, Any]) -> dict[str, Any]:
    """Regex-only arXiv harvest from ``references_benchmark.raw_entries``."""
    rb = gold.get("references_benchmark") or {}
    entries = rb.get("raw_entries") or []
    blob = "\n".join(str(e) for e in entries)
    ids = collect_arxiv_ids_from_text(blob)
    return {
        "arxiv_ids_from_bibliography": ids,
        "count": len(ids),
        "source": "regex_on_references_benchmark.raw_entries",
    }


def _read_article_header(article_path: Path, max_lines: int) -> str:
    """Return the first ``max_lines`` lines of ``article.md`` as a single string."""
    lines = article_path.read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[:max_lines])


def _parse_json_from_llm_content(content: str) -> dict[str, Any]:
    """Parse JSON from an LLM message, stripping optional fenced code blocks."""
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def step_b_llm_header(
    *,
    header_markdown: str,
    api_key: str,
    base_url: str,
    model: str,
    timeout_s: float = 120.0,
) -> dict[str, Any]:
    """Call chat-completions API; return parsed JSON object from assistant message."""
    import httpx  # pylint: disable=import-outside-toplevel

    system = (
        "You extract structured metadata from the beginning of a research paper in Markdown. "
        "Return ONLY valid JSON with exactly these keys: "
        '"year" (integer or null), '
        '"arxiv_id" (string: normalized id like 2005.12872 without version suffix, or null), '
        '"doi" (string or null), '
        '"authors" (array of objects with "name" string and "affiliations" string array). '
        "Use null when unknown. Do not invent identifiers not supported by the header text. "
        "If the paper lists arXiv:YYYY.NNNNNvN, strip the version suffix in arxiv_id."
    )
    user = "Paper header (markdown, first lines only):\n\n" + header_markdown
    url = base_url.rstrip("/") + "/chat/completions"
    payload: dict[str, Any] = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=timeout_s) as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
    content = data["choices"][0]["message"]["content"]
    return _parse_json_from_llm_content(str(content))


def _build_enrichment_payload(
    *,
    case_id: str,
    step_a: dict[str, Any],
    step_b: dict[str, Any] | None,
    dry_run: bool,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "case_id": case_id,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "step_a_arxiv_from_bibliography": step_a,
        "step_b_header_metadata": step_b,
    }


def normalize_header_llm_payload(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize raw LLM JSON into work metadata + authorship list fields."""
    year = raw.get("year")
    if year is not None:
        try:
            year = int(year)
        except (TypeError, ValueError):
            year = None
    arxiv_id = raw.get("arxiv_id")
    if arxiv_id is not None:
        arxiv_id = str(arxiv_id).strip() or None
        if arxiv_id:
            arxiv_id = re.sub(r"v\d+$", "", arxiv_id, flags=re.IGNORECASE)
    doi = raw.get("doi")
    if doi is not None:
        doi = str(doi).strip() or None
    authors_out: list[dict[str, Any]] = []
    for row in raw.get("authors") or []:
        if not isinstance(row, dict):
            continue
        name = (row.get("name") or "").strip()
        if not name:
            continue
        affs = row.get("affiliations") or []
        if not isinstance(affs, list):
            affs = []
        affs = [str(a).strip() for a in affs if str(a).strip()]
        authors_out.append({"name": name, "affiliations": affs})
    return {"year": year, "arxiv_id": arxiv_id, "doi": doi, "authors": authors_out}


def apply_enrichment(  # pylint: disable=too-many-locals
    case_dir: Path,
    enrichment: dict[str, Any],
    *,
    with_quality_thresholds: bool,
) -> None:
    """Merge ``gold_enrichment_*.json`` payload into ``gold.json`` and validate."""
    gold_path = case_dir / "gold.json"
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    step_a = enrichment.get("step_a_arxiv_from_bibliography") or {}
    step_b = enrichment.get("step_b_header_metadata")

    ids = step_a.get("arxiv_ids_from_bibliography")
    if isinstance(ids, list) and ids:
        refs = gold.setdefault("references", {})
        refs["sample_arxiv_ids"] = [str(x) for x in ids]

    if isinstance(step_b, dict) and step_b:
        norm = normalize_header_llm_payload(step_b)
        wm = gold.setdefault("work_metadata", {})
        if norm["year"] is not None:
            wm["publication_year"] = norm["year"]
        if norm["arxiv_id"]:
            wm["arxiv_id"] = norm["arxiv_id"]
        if norm["doi"]:
            wm["doi"] = norm["doi"]
        if norm["authors"]:
            gold["authorships"] = norm["authors"]

    if with_quality_thresholds:
        qt = gold.get("quality_thresholds")
        if not isinstance(qt, dict):
            qt = {}
        has_authors = bool(gold.get("authorships"))
        has_arxiv_sample = bool((gold.get("references") or {}).get("sample_arxiv_ids"))
        if has_authors:
            qt["min_authorship_names_f1"] = DEFAULT_MIN_AUTHORSHIP_NAMES_F1
        if has_arxiv_sample:
            qt["min_sample_arxiv_f1"] = DEFAULT_MIN_SAMPLE_ARXIV_F1
        gold["quality_thresholds"] = qt

    desc = gold.get("description") or ""
    tag = "[gold enriched via scripts/enrich_gold_layer1.py]"
    if tag not in desc:
        gold["description"] = (desc + " " + tag).strip()

    Layer1GoldSpec.model_validate(gold)
    gold_path.write_text(json.dumps(gold, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _discover_cases(fixtures_root: Path, args: argparse.Namespace) -> list[Path]:
    """Resolve case directories from ``--cases`` or ``--all-nightly``."""
    if args.all_nightly:
        manifest = json.loads((fixtures_root / "case_tiers.json").read_text(encoding="utf-8"))
        ids = list(manifest.get("nightly_heavy") or [])
        return [fixtures_root / cid for cid in sorted(ids)]
    out: list[Path] = []
    for cid in args.cases:
        p = fixtures_root / cid
        if not p.is_dir():
            raise SystemExit(f"Missing case directory: {p}")
        out.append(p)
    return out


def run_one(  # pylint: disable=too-many-locals
    case_dir: Path,
    *,
    dry_run: bool,
    skip_llm: bool,
    header_lines: int,
) -> Path:
    """Run enrichment for one case directory; write ``gold_enrichment_<case_id>.json``."""
    gold_path = case_dir / "gold.json"
    article_path = case_dir / "article.md"
    if not gold_path.is_file():
        raise SystemExit(f"Missing {gold_path}")
    if not article_path.is_file():
        raise SystemExit(f"Missing {article_path}")

    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    case_id = str(gold.get("case_id") or case_dir.name)
    step_a = step_a_from_gold(gold)
    step_b: dict[str, Any] | None = None

    if not dry_run and not skip_llm:
        api_key = os.environ.get("TESTGEN_LLM_API_KEY", "")
        base_url = os.environ.get("TESTGEN_LLM_BASE_URL", "").strip()
        model = os.environ.get("TESTGEN_LLM_MODEL", "").strip()
        if not api_key or not base_url or not model:
            raise SystemExit(
                "LLM step requires TESTGEN_LLM_API_KEY, TESTGEN_LLM_BASE_URL, TESTGEN_LLM_MODEL "
                "(or use --dry-run / --regex-only)."
            )
        header = _read_article_header(article_path, header_lines)
        step_b = step_b_llm_header(
            header_markdown=header,
            api_key=api_key,
            base_url=base_url,
            model=model,
        )
    elif dry_run:
        step_b = None

    payload = _build_enrichment_payload(
        case_id=case_id,
        step_a=step_a,
        step_b=step_b,
        dry_run=dry_run or skip_llm,
    )
    out_path = case_dir / f"gold_enrichment_{case_id}.json"
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out_path.relative_to(ROOT)}")
    return out_path


def main() -> None:  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    """CLI entry."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixtures-root",
        type=Path,
        default=FIXTURE_LAYER1,
        help="Layer-1 benchmarks root (default: tests/fixtures/benchmarks/layer1).",
    )
    parser.add_argument(
        "--cases", nargs="*", default=[], help="Case directory names under fixtures root."
    )
    parser.add_argument(
        "--all-nightly",
        action="store_true",
        help="Run for every case_id listed under nightly_heavy in case_tiers.json.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Regex step only; skip LLM (step_b will be null in the enrichment file).",
    )
    parser.add_argument(
        "--regex-only",
        action="store_true",
        help="Alias for --dry-run.",
    )
    parser.add_argument("--header-lines", type=int, default=DEFAULT_HEADER_LINES)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Merge an existing gold_enrichment_<case>.json into gold.json (validates spec).",
    )
    parser.add_argument(
        "--no-quality-thresholds",
        action="store_true",
        help="With --apply, do not inject min_authorship_names_f1 / min_sample_arxiv_f1.",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Optional .env path to load TESTGEN_LLM_* variables.",
    )
    args = parser.parse_args()

    fixtures_root = args.fixtures_root.resolve()

    if args.env_file:
        _load_dotenv_file(args.env_file)

    dry = bool(args.dry_run or args.regex_only)

    if args.apply:
        if args.all_nightly or args.cases:
            targets = (
                _discover_cases(fixtures_root, args)
                if args.all_nightly
                else [fixtures_root / c for c in args.cases]
            )
            for case_dir in targets:
                gold_path = case_dir / "gold.json"
                gold = json.loads(gold_path.read_text(encoding="utf-8"))
                case_id = str(gold.get("case_id") or case_dir.name)
                enrich_path = case_dir / f"gold_enrichment_{case_id}.json"
                if not enrich_path.is_file():
                    raise SystemExit(f"Missing enrichment file: {enrich_path}")
                enrichment = json.loads(enrich_path.read_text(encoding="utf-8"))
                apply_enrichment(
                    case_dir,
                    enrichment,
                    with_quality_thresholds=not args.no_quality_thresholds,
                )
                print(f"Applied {enrich_path.relative_to(ROOT)} -> {gold_path.relative_to(ROOT)}")
        else:
            raise SystemExit("--apply requires --cases ... or --all-nightly")
        return

    if not args.cases and not args.all_nightly:
        parser.error("Specify --cases, or use --all-nightly")

    for case_dir in _discover_cases(fixtures_root, args):
        run_one(case_dir, dry_run=dry, skip_llm=dry, header_lines=args.header_lines)


if __name__ == "__main__":
    main()
