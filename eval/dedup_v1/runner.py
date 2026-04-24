"""Offline precision/recall benchmark for Wave L work dedup."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from itertools import combinations
from pathlib import Path

import typer

from science_graphrag.dedup.fingerprints import work_pair_fingerprint

STOPWORDS = {
    "a",
    "an",
    "and",
    "for",
    "in",
    "of",
    "on",
    "the",
    "to",
    "with",
    "version",
    "journal",
}


@dataclass(frozen=True)
class WorkRecord:
    work_id: str
    title: str
    year: int | None
    first_author: str
    abstract: str


def _fixture_dir() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "tests"
        / "fixtures"
        / "benchmarks"
        / "dedup_v1"
    )


def _normalize_text(text: str) -> str:
    norm = str(text or "").lower()
    # Normalize "covid19" <-> "covid-19" style variants for stable token overlap.
    norm = re.sub(r"([a-z])([0-9])", r"\1 \2", norm)
    norm = re.sub(r"([0-9])([a-z])", r"\1 \2", norm)
    return " ".join(re.findall(r"[a-z0-9]+", norm))


def _token_set(text: str) -> set[str]:
    return {t for t in _normalize_text(text).split() if t and t not in STOPWORDS}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


def _title_similarity(a: str, b: str) -> float:
    token_sim = _jaccard(_token_set(a), _token_set(b))
    seq_sim = SequenceMatcher(None, _normalize_text(a), _normalize_text(b)).ratio()
    return 0.6 * token_sim + 0.4 * seq_sim


def _author_similarity(a: str, b: str) -> float:
    a_norm = _normalize_text(a)
    b_norm = _normalize_text(b)
    if not a_norm or not b_norm:
        return 0.0
    return SequenceMatcher(None, a_norm, b_norm).ratio()


def _abstract_similarity(a: str, b: str) -> float:
    return _jaccard(_token_set(a), _token_set(b))


def _is_probable_duplicate(left: WorkRecord, right: WorkRecord) -> bool:
    t = _title_similarity(left.title, right.title)
    au = _author_similarity(left.first_author, right.first_author)
    ab = _abstract_similarity(left.abstract, right.abstract)
    year_close = (
        left.year is not None and right.year is not None and abs(left.year - right.year) <= 2
    )

    if t >= 0.84 and (au >= 0.55 or year_close or ab >= 0.35):
        return True
    if t >= 0.75 and au >= 0.78 and ab >= 0.22:
        return True
    return False


def _load_gold(path: Path) -> tuple[list[WorkRecord], list[list[str]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("records")
    clusters = data.get("clusters")
    if not isinstance(rows, list) or not rows:
        raise ValueError("gold.json: records[] required")
    if not isinstance(clusters, list) or not clusters:
        raise ValueError("gold.json: clusters[] required")

    records: list[WorkRecord] = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"records[{i}] must be object")
        work_id = str(row.get("work_id") or "").strip()
        if not work_id:
            raise ValueError(f"records[{i}].work_id required")
        year_raw = row.get("year")
        year = int(year_raw) if year_raw is not None else None
        records.append(
            WorkRecord(
                work_id=work_id,
                title=str(row.get("title") or ""),
                year=year,
                first_author=str(row.get("first_author") or ""),
                abstract=str(row.get("abstract") or ""),
            ),
        )
    return records, [[str(x) for x in c] for c in clusters if isinstance(c, list)]


def _metrics(records: list[WorkRecord], clusters: list[list[str]]) -> dict[str, float | int]:
    cluster_sets = [set(c) for c in clusters if len(c) >= 2]
    positives: set[tuple[str, str]] = set()
    for c in cluster_sets:
        for a, b in combinations(sorted(c), 2):
            positives.add((a, b))

    predicted: set[tuple[str, str]] = set()
    for left, right in combinations(records, 2):
        a, b = sorted((left.work_id, right.work_id))
        fp = work_pair_fingerprint("dedup_v1_fixture", a, b)
        if len(fp) != 64:
            raise ValueError("fingerprint invariant failed")
        if _is_probable_duplicate(left, right):
            predicted.add((a, b))

    tp = len(predicted & positives)
    fp_count = len(predicted - positives)
    fn = len(positives - predicted)

    precision = tp / (tp + fp_count) if (tp + fp_count) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "records": len(records),
        "positive_pairs": len(positives),
        "predicted_pairs": len(predicted),
        "tp": tp,
        "fp": fp_count,
        "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def main(precision_gate: float = 0.9, recall_gate: float = 0.8) -> None:
    gold_path = _fixture_dir() / "gold.json"
    if not gold_path.is_file():
        raise typer.Exit(code=2)
    records, clusters = _load_gold(gold_path)
    report = _metrics(records, clusters)
    passed = (
        float(report["precision"]) >= float(precision_gate)
        and float(report["recall"]) >= float(recall_gate)
    )
    typer.echo(json.dumps({"passed": passed, **report}, ensure_ascii=False, indent=2))
    if not passed:
        raise typer.Exit(code=1)


def _cli(
    precision_gate: float = typer.Option(0.9, "--precision-gate"),
    recall_gate: float = typer.Option(0.8, "--recall-gate"),
) -> None:
    main(precision_gate=precision_gate, recall_gate=recall_gate)


def cli() -> None:
    typer.run(_cli)


if __name__ == "__main__":
    cli()
