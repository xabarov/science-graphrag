"""Benchmark runner: level-A span metrics and level-B entry overlap (ref_gpt5.4_thoughts)."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from eval.layer1.spec import Layer1GoldSpec
from eval.references_harness.metrics import (
    entry_overlap_micro_f1,
    gold_line_set_for_span_iou,
    line_set_iou_sets,
    line_span_from_char_range,
)
from eval.references_harness.scope_segmentation import (
    pred_raw_entries_from_bibliography_excerpt,
)
from science_graphrag.config import get_settings
from science_graphrag.ingestion.document_slices import (
    build_references_scope_text,
    find_reference_section_spans,
)
from science_graphrag.ingestion.llm.extractor import SyncInstructorExtractor
from science_graphrag.ingestion.llm.schemas import ReferenceBibliographyScopeLLM
from science_graphrag.ingestion.llm.stage_extraction import (
    SYSTEM_FENCE,
    _merge_reference_sets,
    _reference_chunk_groups,
    _references_from_llm,
)
from science_graphrag.ingestion.stages.references import extract_references

Mode = Literal[
    "heuristic_full",
    "heuristic_scope",
    "heuristic_bib_gold",
    "scope_llm",
    "batched_llm",
]


@dataclass
class RefBenchCaseReport:
    case_id: str
    mode: str
    gold_start_line: int
    gold_end_line: int
    pred_start_line: int
    pred_end_line: int
    span_line_iou: float
    span_start_abs_err: int
    span_end_abs_err: int
    gold_entry_count: int
    pred_entry_count: int
    count_abs_error: int
    entry_overlap_f1: float
    entry_overlap_precision: float
    entry_overlap_recall: float
    scope_llm_status: str | None = None
    scope_llm_fallback: bool | None = None
    error: str | None = None
    wall_seconds: float = 0.0

    def as_json_dict(self) -> dict[str, Any]:
        return asdict(self)


def _line_set_from_char_spans(text: str, spans: list[tuple[int, int]]) -> set[int]:
    lines: set[int] = set()
    for start_c, end_c in spans:
        a, b = line_span_from_char_range(text, start_c, end_c)
        if b >= a:
            lines.update(range(a, b + 1))
    return lines


def _pred_line_span_heuristic(text: str) -> tuple[int, int, set[int]]:
    spans = find_reference_section_spans(text)
    if not spans:
        n = len(text.splitlines())
        return (max(1, n), n, set(range(1, n + 1)))
    line_set = _line_set_from_char_spans(text, spans)
    if not line_set:
        return (1, 0, set())
    return (min(line_set), max(line_set), line_set)


def _line_span_from_excerpt(text: str, excerpt: str) -> tuple[int, int, set[int]]:
    excerpt = excerpt.strip()
    if not excerpt:
        return (1, 0, set())
    prefix = excerpt[: min(200, len(excerpt))]
    idx = text.find(prefix)
    if idx < 0:
        head = excerpt.split("\n", 1)[0].strip()[:100]
        idx = text.find(head)
    if idx < 0:
        return (1, 0, set())
    start_c = idx
    end_c = idx + len(excerpt)
    a, b = line_span_from_char_range(text, start_c, end_c)
    line_set = set(range(a, b + 1)) if b >= a else set()
    return (a, b, line_set)


def _pred_raw_heuristic_scope(refs_scope: str) -> list[str]:
    # Heuristic parser expects heading context; scope text is usually body-only.
    chunk = "# Synthetic\n\n## References\n\n" + refs_scope.strip()
    return [r.raw_reference.strip() for r in extract_references(chunk) if r.raw_reference]


def _pred_raw_heuristic_full(text: str) -> list[str]:
    return [r.raw_reference.strip() for r in extract_references(text) if r.raw_reference]


def _pred_raw_heuristic_bib_gold_slice(text: str, gold_start: int, gold_end: int) -> list[str]:
    """``extract_references`` on gold bibliography lines only (plan A3)."""
    lines = text.splitlines()
    if gold_start < 1 or gold_end > len(lines) or gold_end < gold_start:
        return []
    block = "\n".join(lines[gold_start - 1 : gold_end])
    chunk = "# Synthetic\n\n## References\n\n" + block
    return [r.raw_reference.strip() for r in extract_references(chunk) if r.raw_reference]


def run_case(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    fixture_root: Path,
    case_id: str,
    mode: Mode,
    *,
    settings: Any | None = None,
) -> RefBenchCaseReport:
    t0 = time.perf_counter()

    def _dt() -> float:
        return round(time.perf_counter() - t0, 3)

    gold_path = fixture_root / case_id / "gold.json"
    article_path = fixture_root / case_id / "article.md"
    spec = Layer1GoldSpec.load(gold_path)
    rb = spec.references_benchmark
    if rb is None:
        return RefBenchCaseReport(
            case_id=case_id,
            mode=mode,
            gold_start_line=0,
            gold_end_line=0,
            pred_start_line=0,
            pred_end_line=0,
            span_line_iou=0.0,
            span_start_abs_err=0,
            span_end_abs_err=0,
            gold_entry_count=0,
            pred_entry_count=0,
            count_abs_error=0,
            entry_overlap_f1=0.0,
            entry_overlap_precision=0.0,
            entry_overlap_recall=0.0,
            error="missing references_benchmark in gold.json",
            wall_seconds=_dt(),
        )

    s = settings or get_settings()
    text = article_path.read_text(encoding="utf-8")
    article_lines = text.splitlines()
    g0, g1 = rb.bibliography.start_line, rb.bibliography.end_line
    gold_set = gold_line_set_for_span_iou(article_lines, g0, g1)
    gold_entries = rb.raw_entries

    refs_scope = build_references_scope_text(
        text,
        max_chars=s.references_scope_max_chars,
    )

    scope_status: str | None = None
    scope_fb: bool | None = None
    pred_entries: list[str] = []

    if mode == "scope_llm":
        api = (s.benchmark_teacher_llm_api_key or s.extraction_llm_api_key or "").strip()
        if not api:
            return RefBenchCaseReport(
                case_id=case_id,
                mode=mode,
                gold_start_line=g0,
                gold_end_line=g1,
                pred_start_line=0,
                pred_end_line=0,
                span_line_iou=0.0,
                span_start_abs_err=0,
                span_end_abs_err=0,
                gold_entry_count=len(gold_entries),
                pred_entry_count=0,
                count_abs_error=abs(len(gold_entries) - 0),
                entry_overlap_f1=0.0,
                entry_overlap_precision=0.0,
                entry_overlap_recall=0.0,
                error="no API key for scope_llm",
                wall_seconds=_dt(),
            )
        extractor = SyncInstructorExtractor(
            api_key=api,
            base_url=s.extraction_llm_base_url,
            model=s.extraction_llm_model,
            temperature=s.extraction_llm_temperature,
            max_tokens=min(s.extraction_llm_max_tokens_references, 16_384),
            timeout_seconds=s.extraction_llm_timeout_seconds,
            mode=s.extraction_llm_mode,
        )
        user_scope = (
            "Identify the bibliography / references block in the markdown below. "
            "Return references_block_excerpt as verbatim lines of the bibliography only "
            "(all entries, no surrounding sections). "
            "Set bibliography_style_hint to numbered, author_year, or auto. "
            "Optionally set confidence in [0,1].\n\n---\n"
        )
        truncated = refs_scope if len(refs_scope) < len(text) else text
        parsed, err = extractor.extract_maybe(
            ReferenceBibliographyScopeLLM,
            system=SYSTEM_FENCE
            + " Bibliography location only; excerpt must be copy-paste from the text.",
            user=user_scope + truncated,
        )
        excerpt_for_parse = refs_scope
        scope_fb = False
        if err or parsed is None:
            scope_status = (err or "llm_empty_result")[:200]
            scope_fb = True
        else:
            scope_status = "ok"
            excerpt = (parsed.references_block_excerpt or "").strip()
            if len(excerpt) < 80 and (parsed.confidence is None or parsed.confidence < 0.35):
                scope_fb = True
            else:
                excerpt_for_parse = excerpt
        style_hint = None if parsed is None else parsed.bibliography_style_hint
        pred_entries = pred_raw_entries_from_bibliography_excerpt(
            excerpt_for_parse,
            style_hint,
        )
        ps, pe, pred_set = _line_span_from_excerpt(text, excerpt_for_parse)
        if not pred_set:
            ps, pe, pred_set = _pred_line_span_heuristic(text)
    elif mode == "batched_llm":
        from science_graphrag.ingestion.llm.schemas import ReferenceIdsOnlyLLM

        api = (s.benchmark_teacher_llm_api_key or s.extraction_llm_api_key or "").strip()
        if not api:
            return RefBenchCaseReport(
                case_id=case_id,
                mode=mode,
                gold_start_line=g0,
                gold_end_line=g1,
                pred_start_line=0,
                pred_end_line=0,
                span_line_iou=0.0,
                span_start_abs_err=0,
                span_end_abs_err=0,
                gold_entry_count=len(gold_entries),
                pred_entry_count=0,
                count_abs_error=abs(len(gold_entries) - 0),
                entry_overlap_f1=0.0,
                entry_overlap_precision=0.0,
                entry_overlap_recall=0.0,
                error="no API key for batched_llm",
                wall_seconds=_dt(),
            )
        extractor = SyncInstructorExtractor(
            api_key=api,
            base_url=s.extraction_llm_base_url,
            model=s.extraction_llm_model,
            temperature=s.extraction_llm_temperature,
            max_tokens=s.extraction_llm_max_tokens_references,
            timeout_seconds=s.extraction_llm_timeout_seconds,
            mode=s.extraction_llm_mode,
        )
        ps, pe, pred_set = _pred_line_span_heuristic(text)
        ref_entry_groups = _reference_chunk_groups(
            refs_scope, s.extraction_llm_references_batch_size
        )
        ref_chunks = [
            "\n".join(entry.strip() for entry in group if entry).strip()
            for group in ref_entry_groups
        ]
        heuristic_refs = extract_references(text)
        all_items: list = []
        refs_instruction = (
            "Extract bibliography entries from the references section. For each entry include "
            "raw_reference (full bibliography line or merged wrapped lines), doi if present, "
            "and arxiv_id (YYMM.NNNNN) if the line mentions arXiv or abs/."
        )
        for chunk in ref_chunks:
            parsed, err = extractor.extract_maybe(
                ReferenceIdsOnlyLLM,
                system=(
                    SYSTEM_FENCE
                    + " References list only; preserve one bibliography item per entry "
                    "and capture DOI/arXiv identifiers faithfully."
                ),
                user=f"{refs_instruction}\n\n---\n{chunk}",
            )
            if not err and parsed is not None:
                all_items.extend(parsed.references)
        llm_refs = _references_from_llm(all_items, include_titles=False)
        merged_refs, _merge_stats = _merge_reference_sets(
            heuristic_refs,
            llm_refs,
            mode=s.extraction_llm_references_merge_policy,
            max_extra_beyond_heuristic=s.extraction_llm_references_merge_max_extra,
        )
        pred_entries = [r.raw_reference.strip() for r in merged_refs if r.raw_reference]
    elif mode == "heuristic_scope":
        ps, pe, pred_set = _pred_line_span_heuristic(text)
        pred_entries = _pred_raw_heuristic_scope(refs_scope)
    elif mode == "heuristic_bib_gold":
        ps, pe, pred_set = _pred_line_span_heuristic(text)
        pred_entries = _pred_raw_heuristic_bib_gold_slice(text, g0, g1)
    else:
        ps, pe, pred_set = _pred_line_span_heuristic(text)
        pred_entries = _pred_raw_heuristic_full(text)

    span_iou = line_set_iou_sets(gold_set, pred_set)
    start_err = abs(ps - g0) if pe >= ps else 999
    end_err = abs(pe - g1) if pe >= ps else 999

    ov = entry_overlap_micro_f1(gold_entries, pred_entries)

    return RefBenchCaseReport(
        case_id=case_id,
        mode=mode,
        gold_start_line=g0,
        gold_end_line=g1,
        pred_start_line=ps,
        pred_end_line=pe,
        span_line_iou=span_iou,
        span_start_abs_err=start_err,
        span_end_abs_err=end_err,
        gold_entry_count=len(gold_entries),
        pred_entry_count=len(pred_entries),
        count_abs_error=abs(len(gold_entries) - len(pred_entries)),
        entry_overlap_f1=ov["f1"],
        entry_overlap_precision=ov["precision"],
        entry_overlap_recall=ov["recall"],
        scope_llm_status=scope_status,
        scope_llm_fallback=scope_fb,
        error=None,
        wall_seconds=_dt(),
    )


def run_suite(
    fixture_root: Path,
    case_ids: list[str],
    mode: Mode,
    *,
    settings: Any | None = None,
) -> list[dict[str, Any]]:
    """Run ``run_case`` for each case id."""
    rows: list[dict[str, Any]] = []
    for c in case_ids:
        rows.append(run_case(fixture_root, c, mode, settings=settings).as_json_dict())
    return rows


def write_summary(
    out_dir: Path,
    by_mode: dict[str, list[dict[str, Any]]],
    *,
    cli_wall_seconds: float | None = None,
) -> None:
    """Write per-mode JSON rows and aggregated ``refs_bench_summary.json``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {
        "modes": list(by_mode.keys()),
        "per_mode_mean": {},
        "cases": {},
    }
    if cli_wall_seconds is not None:
        summary["cli_wall_seconds"] = round(cli_wall_seconds, 3)
    for mode, rows in by_mode.items():
        ok = [r for r in rows if not r.get("error")]
        ious = [r["span_line_iou"] for r in ok]
        f1s = [r["entry_overlap_f1"] for r in ok]
        walls = [float(r.get("wall_seconds") or 0.0) for r in rows]
        summary["per_mode_mean"][mode] = {
            "mean_span_line_iou": sum(ious) / len(ious) if ious else 0.0,
            "mean_entry_overlap_f1": sum(f1s) / len(f1s) if f1s else 0.0,
            "n_ok": len(ok),
            "n_total": len(rows),
            "total_wall_seconds": round(sum(walls), 3),
            "mean_wall_seconds_per_case": round(sum(walls) / len(walls), 3) if walls else 0.0,
        }
        for r in rows:
            cid = r["case_id"]
            summary["cases"].setdefault(cid, {})[mode] = r

    (out_dir / "refs_bench_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    for mode, rows in by_mode.items():
        (out_dir / f"refs_bench_{mode}.json").write_text(
            json.dumps(rows, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
