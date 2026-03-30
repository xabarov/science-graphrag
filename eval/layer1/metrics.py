"""Metric helpers for layer-1 extraction benchmarks."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from science_graphrag.domain.models import AuthorshipDraft, ReferenceDraft, WorkDraft, WorkType
from science_graphrag.ingestion.dedup import normalize_doi

from .spec import Layer1GoldSpec

_ARXIV_IN_TEXT_RE = re.compile(
    r"(?:arxiv:\s*)?(\d{4}\.\d{4,5})\b|abs/(\d{4}\.\d{4,5})\b",
    re.IGNORECASE,
)


def _norm_ws(s: str | None) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", s.strip()).lower()


def _norm_aff(s: str) -> str:
    return _norm_ws(s)


def prf1_tp_fp_fn(gold: set[str], pred: set[str]) -> tuple[float, float, float, int, int, int]:
    """Micro-F1 over string sets (gold / predicted identifiers)."""
    if not gold and not pred:
        return 1.0, 1.0, 1.0, 0, 0, 0
    tp = len(gold & pred)
    fp = len(pred - gold)
    fn = len(gold - pred)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1, tp, fp, fn


def _arxiv_groups(m: re.Match[str]) -> str:
    return m.group(1) or m.group(2)


def collect_arxiv_from_reference(r: ReferenceDraft) -> set[str]:
    out: set[str] = set()
    aid = getattr(r, "arxiv_id", None)
    if aid and str(aid).strip():
        out.add(str(aid).strip())
    for chunk in (r.raw_reference or "", r.title or ""):
        for m in _ARXIV_IN_TEXT_RE.finditer(chunk):
            out.add(_arxiv_groups(m))
    return out


def collect_doi_from_reference(r: ReferenceDraft) -> set[str]:
    out: set[str] = set()
    if r.doi:
        d = normalize_doi(r.doi)
        if d:
            out.add(d)
    dm = re.search(r"\b(10\.\d{4,9}/\S+)\b", r.raw_reference or "", re.IGNORECASE)
    if dm:
        d = normalize_doi(dm.group(1))
        if d:
            out.add(d)
    return out


@dataclass
class BenchmarkMetrics:
    """Aggregated scores for one benchmark case."""

    metadata: dict[str, Any] = field(default_factory=dict)
    authorships: dict[str, Any] = field(default_factory=dict)
    references: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata,
            "authorships": self.authorships,
            "references": self.references,
        }


def _metadata_scores(work: WorkDraft, gold: Layer1GoldSpec) -> dict[str, Any]:
    gm = gold.work_metadata
    title_match = None
    if gm.title:
        title_match = _norm_ws(work.title) == _norm_ws(gm.title)
    year_match = None
    if gm.publication_year is not None:
        year_match = work.publication_year == gm.publication_year
    abstract_ok = None
    if gm.abstract_prefix:
        ab = _norm_ws(work.abstract)
        abstract_ok = ab.startswith(_norm_ws(gm.abstract_prefix))
    doi_match = None
    if gm.doi is not None:
        doi_match = normalize_doi(work.doi) == normalize_doi(gm.doi)
    arx_match = None
    if gm.arxiv_id is not None:
        arx_match = _norm_ws(work.arxiv_id) == _norm_ws(gm.arxiv_id)
    wt_match = None
    if gm.work_type:
        try:
            exp = WorkType(gm.work_type)
            wt_match = work.work_type == exp
        except ValueError:
            wt_match = work.work_type and work.work_type.value == gm.work_type
    return {
        "title_exact_normalized": title_match,
        "year_exact": year_match,
        "abstract_prefix_ok": abstract_ok,
        "doi_match_expected": doi_match,
        "arxiv_match_expected": arx_match,
        "work_type_match": wt_match,
    }


def _authorship_scores(
    pred: list[AuthorshipDraft],
    gold: Layer1GoldSpec,
) -> dict[str, Any]:
    g_names = [_norm_ws(a.name) for a in gold.authorships]
    p_names = [_norm_ws(a.author_raw_name) for a in pred]
    gold_set = set(g_names)
    pred_set = set(p_names)
    p_n, r_n, f1_n, tp_n, fp_n, fn_n = prf1_tp_fp_fn(gold_set, pred_set)

    order_hits = 0
    for i, gn in enumerate(g_names):
        if i < len(p_names) and p_names[i] == gn:
            order_hits += 1
    denom = max(len(g_names), len(p_names), 1)
    order_accuracy = order_hits / denom

    aff_jaccards: list[float] = []
    for ga in gold.authorships:
        gn = _norm_ws(ga.name)
        pa = next((x for x in pred if _norm_ws(x.author_raw_name) == gn), None)
        if not pa:
            continue
        g_affs = {_norm_aff(x) for x in ga.affiliations if x.strip()}
        p_affs = {_norm_aff(x) for x in pa.raw_affiliations if x.strip()}
        if not g_affs and not p_affs:
            aff_jaccards.append(1.0)
            continue
        inter = g_affs & p_affs
        union = g_affs | p_affs
        aff_jaccards.append(len(inter) / len(union) if union else 0.0)
    affiliation_jaccard_macro = sum(aff_jaccards) / len(aff_jaccards) if aff_jaccards else 0.0

    gold_aff_flat = {_norm_aff(x) for a in gold.authorships for x in a.affiliations if x.strip()}
    pred_aff_flat = {_norm_aff(x) for a in pred for x in a.raw_affiliations if x.strip()}
    p_aff, r_aff, f1_aff, _, _, _ = prf1_tp_fp_fn(gold_aff_flat, pred_aff_flat)

    return {
        "names_precision": p_n,
        "names_recall": r_n,
        "names_f1": f1_n,
        "names_tp_fp_fn": {"tp": tp_n, "fp": fp_n, "fn": fn_n},
        "order_accuracy": order_accuracy,
        "order_hits": order_hits,
        "affiliation_jaccard_macro_on_matched_authors": affiliation_jaccard_macro,
        "affiliations_precision": p_aff,
        "affiliations_recall": r_aff,
        "affiliations_f1": f1_aff,
        "pred_count": len(pred),
        "gold_count": len(gold.authorships),
    }


def _reference_scores(refs: list[ReferenceDraft], gold: Layer1GoldSpec) -> dict[str, Any]:
    gr = gold.references
    count = len(refs)
    min_c = gr.min_count if gr.min_count is not None else gr.expected_count
    count_ok = min_c <= count <= gr.expected_count + 2
    count_delta = count - gr.expected_count

    gold_arx = {x.strip() for x in gr.sample_arxiv_ids}
    pred_arx: set[str] = set()
    for r in refs:
        pred_arx |= collect_arxiv_from_reference(r)
    p_a, r_a, f1_a, tp_a, fp_a, fn_a = prf1_tp_fp_fn(gold_arx, pred_arx)

    gold_dois = {normalize_doi(d) for d in gr.sample_dois if d}
    gold_dois.discard(None)
    pred_dois: set[str] = set()
    for r in refs:
        pred_dois |= collect_doi_from_reference(r)
    pred_dois = {d for d in pred_dois if d}
    p_d, r_d, f1_d, _, _, _ = prf1_tp_fp_fn(gold_dois, pred_dois)

    return {
        "count": count,
        "expected_count": gr.expected_count,
        "min_count": gr.min_count,
        "count_ok": count_ok,
        "count_delta": count_delta,
        "sample_arxiv_precision": p_a,
        "sample_arxiv_recall": r_a,
        "sample_arxiv_f1": f1_a,
        "sample_arxiv_tp_fp_fn": {"tp": tp_a, "fp": fp_a, "fn": fn_a},
        "predicted_arxiv_ids": sorted(pred_arx),
        "sample_doi_precision": p_d,
        "sample_doi_recall": r_d,
        "sample_doi_f1": f1_d,
    }


def score_layer1(
    work: WorkDraft,
    authorships: list[AuthorshipDraft],
    references: list[ReferenceDraft],
    gold: Layer1GoldSpec,
) -> BenchmarkMetrics:
    return BenchmarkMetrics(
        metadata=_metadata_scores(work, gold),
        authorships=_authorship_scores(authorships, gold),
        references=_reference_scores(references, gold),
    )
