#!/usr/bin/env python3
"""
Generate docs/benchmarks/benchmark-metrics-values.md from committed eval/results/*.json.

Usage (repo root):
  .venv/bin/python scripts/generate_benchmark_metrics_tables.py
  .venv/bin/python scripts/generate_benchmark_metrics_tables.py \\
    --out docs/benchmarks/benchmark-metrics-values.md
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUMMARY = ROOT / "eval/results/benchmark-metrics-summary.json"
DEFAULT_OUT = ROOT / "docs/benchmarks/benchmark-metrics-values.md"


# ── Low-level helpers ────────────────────────────────────────────────────────

def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _tick(v: Any) -> str:
    """Boolean → ✓ / ✗ / —."""
    if v is None:
        return "—"
    return "✓" if v else "✗"


def _f2(v: Any) -> str:
    """Float → 2-decimal string, or — if absent/NaN."""
    if v is None or v == "":
        return "—"
    try:
        fv = float(v)
        return "—" if math.isnan(fv) else f"{fv:.2f}"
    except (TypeError, ValueError):
        return "—"


def _case_label(cid: str) -> str:
    """Strip _realpdf / _semantic suffixes for display."""
    for suffix in ("_realpdf", "_semantic"):
        if cid.endswith(suffix):
            return cid[: -len(suffix)]
    return cid


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    sep = ["---"] * len(headers)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(sep) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n"


def _iter_cases(data: dict[str, Any]) -> list[dict[str, Any]]:
    if "cases" in data:
        return list(data["cases"])
    if "case" in data:
        return [data["case"]]
    return []


# ── Row builders ─────────────────────────────────────────────────────────────

def _layer1_row(case: dict[str, Any], *, show_authors: bool) -> list[str]:
    m = case.get("metrics") or {}
    md = m.get("metadata") or {}
    au = m.get("authorships") or {}
    rf = m.get("references") or {}
    ct = m.get("contract") or {}
    has_gold = int(au.get("gold_count") or 0) > 0
    names_f1 = _f2(au.get("names_f1")) if has_gold else "—"
    row = [_case_label(case.get("case_id", "")), _tick(md.get("title_exact_normalized"))]
    if show_authors:
        row.append(names_f1)
    row += [_f2(rf.get("sample_arxiv_f1")), _tick(rf.get("count_ok")), _tick(ct.get("passed"))]
    return row


def _layer1_headers(*, show_authors: bool) -> list[str]:
    base = ["Статья", "Заголовок ✓"]
    if show_authors:
        base.append("Авторы F1")
    base += ["arXiv-ссылки F1", "Кол-во ссылок ✓", "Контракт ✓"]
    return base


def _graph_row(case: dict[str, Any]) -> list[str]:
    m = case.get("metrics") or {}
    ct = m.get("contract") or {}
    snap = m.get("snapshot") or {}
    return [
        _case_label(case.get("case_id", "")),
        _f2(m.get("cited_arxiv_precision")),
        _f2(m.get("cited_arxiv_recall")),
        _f2(m.get("cited_arxiv_f1")),
        str(snap.get("cites_count") or "—"),
        _tick(ct.get("passed")),
    ]


def _layer2_row(case: dict[str, Any]) -> list[str]:
    m = case.get("metrics") or {}
    rm_num = m.get("recall_methods_num")
    rm_den = m.get("recall_methods_denom")
    rd_num = m.get("recall_datasets_num")
    rd_den = m.get("recall_datasets_denom")
    r_m = f"{rm_num}/{rm_den}" if rm_den not in (None, 0) else "—"
    r_d = f"{rd_num}/{rd_den}" if rd_den not in (None, 0) else "—"
    return [
        _case_label(case.get("case_id", "")),
        _f2(m.get("precision_methods")),
        r_m,
        _f2(m.get("precision_datasets")),
        r_d,
        _tick(m.get("passed")),
    ]


def _claims_row(case: dict[str, Any]) -> list[str]:
    m = case.get("metrics") or {}
    return [
        case.get("case_id", ""),
        str(m.get("expected_count") if m.get("expected_count") is not None else "—"),
        _f2(m.get("claim_recall")),
        _f2(m.get("claim_precision")),
        _tick(m.get("passed")),
    ]


def _refs_res_row(case: dict[str, Any]) -> list[str]:
    m = case.get("metrics") or {}
    return [
        case.get("case_id", ""),
        str(m.get("expected_count") if m.get("expected_count") is not None else "—"),
        _f2(m.get("resolution_recall")),
        _f2(m.get("resolution_precision")),
        _tick(m.get("passed")),
    ]


# ── Aggregate helpers ────────────────────────────────────────────────────────

def _collect(cases: list[dict[str, Any]], *keys: str) -> list[float]:
    """Walk a dotted key path in metrics and collect float values."""
    vals: list[float] = []
    for c in cases:
        node: Any = c.get("metrics") or {}
        for k in keys:
            if not isinstance(node, dict):
                node = None
                break
            node = node.get(k)
        if node is None:
            continue
        try:
            vals.append(float(node))
        except (TypeError, ValueError):
            pass
    return vals


def _mean_str(vals: list[float]) -> str:
    return f"{statistics.mean(vals):.2f}" if vals else "—"


def _count_passed(cases: list[dict[str, Any]], *keys: str) -> int:
    """Count cases where the nested key path equals True."""
    count = 0
    for c in cases:
        node: Any = c.get("metrics") or {}
        for k in keys:
            if not isinstance(node, dict):
                node = None
                break
            node = node.get(k)
        if node is True:
            count += 1
    return count


def _layer1_summary(cases: list[dict[str, Any]]) -> str:
    n = len(cases)
    passed = _count_passed(cases, "contract", "passed")
    arxiv_vals = _collect(cases, "references", "sample_arxiv_f1")
    parts = [f"**{passed}/{n}** прошли контракт"]
    if arxiv_vals:
        parts.append(
            f"среднее F1 arXiv-ссылок = **{_mean_str(arxiv_vals)}** (n={len(arxiv_vals)})"
        )
    return " · ".join(parts)


def _layer2_summary(cases: list[dict[str, Any]]) -> str:
    n = len(cases)
    passed = _count_passed(cases, "passed")
    pm_vals = _collect(cases, "precision_methods")
    pd_vals = _collect(cases, "precision_datasets")
    parts = [f"**{passed}/{n}** прошли"]
    if pm_vals:
        parts.append(f"ср. точность методов = **{_mean_str(pm_vals)}**")
    if pd_vals:
        parts.append(f"ср. точность датасетов = **{_mean_str(pd_vals)}**")
    return " · ".join(parts)


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    """Read benchmark-metrics-summary.json and emit clean markdown metric tables."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    summary_path: Path = args.summary
    out_path: Path = args.out

    if not summary_path.is_file():
        raise SystemExit(f"Missing summary JSON: {summary_path}")

    summary = _read(summary_path)
    auth = summary.get("authoritative_artifacts") or {}
    gen_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines: list[str] = []

    lines.append("# Метрики бенчмарков\n")
    lines.append(
        f"Сгенерировано: {gen_at}  \n"
        "Перегенерировать: `.venv/bin/python scripts/generate_benchmark_metrics_tables.py`  \n"
        "Смысл метрик: [benchmark-metrics-catalog.md](benchmark-metrics-catalog.md)\n"
    )

    # ── Статус системы ────────────────────────────────────────────────────────
    l1n = summary.get("layer1_nightly") or {}
    l2n = summary.get("layer2_nightly") or {}
    decision = (summary.get("decision_gate") or {}).get("decision")
    if l1n or decision:
        lines.append("---\n")
        lines.append("## Статус системы\n")
        status_rows: list[list[str]] = []
        if decision:
            status_rows.append(["Решение gate", f"**{decision}**"])
        if l1n:
            fc = l1n.get("failed_count")
            ev = l1n.get("references_llm_failed_events")
            status_rows.append(["Layer-1 nightly — не прошли", str(fc) if fc is not None else "—"])
            status_rows.append(
                ["Layer-1 nightly — сбоев LLM-ссылок", str(ev) if ev is not None else "—"]
            )
        if l2n:
            fc2 = l2n.get("failed_count")
            status_rows.append(
                ["Layer-2 nightly — не прошли", str(fc2) if fc2 is not None else "—"]
            )
        lines.append(_md_table(["Показатель", "Значение"], status_rows))
        lines.append("")

    # ── 1. Эталонный прогон (YOLOv1) ─────────────────────────────────────────
    ref_paths = auth.get("reference") or []
    ref_kinds = [
        ("layer1", "Метаданные статьи"),
        ("graph", "Граф цитирований"),
        ("layer2", "Семантика (методы и датасеты)"),
    ]
    ref_data: dict[str, tuple[dict[str, Any], str]] = {}
    for rel, (kind, _) in zip(ref_paths, ref_kinds):
        path = ROOT / rel
        if path.is_file():
            ref_data[kind] = (_read(path), rel)

    if ref_data:
        lines.append("---\n")
        lines.append("## 1. Эталонный прогон — YOLOv1 (merge_safe)\n")
        lines.append(
            "Базовая статья (YOLOv1, CVPR 2016) используется для контроля регрессий "
            "во всех трёх слоях. Любое изменение чисел сигнализирует о регрессии.\n"
        )

        if "layer1" in ref_data:
            data, rel = ref_data["layer1"]
            cases = _iter_cases(data)
            lines.append("### 1.1 Метаданные статьи\n")
            lines.append(
                "Заголовок, авторы, arXiv-ссылки в библиографии, соответствие числа ссылок.\n"
            )
            lines.append(_md_table(_layer1_headers(show_authors=True),
                                   [_layer1_row(c, show_authors=True) for c in cases]))
            lines.append("")

        if "graph" in ref_data:
            data, rel = ref_data["graph"]
            cases = _iter_cases(data)
            lines.append("### 1.2 Граф цитирований\n")
            lines.append(
                "Precision / Recall / F1 по arXiv-идентификаторам процитированных работ "
                "в графе Neo4j.\n"
            )
            lines.append(_md_table(
                ["Статья", "P (arXiv)", "R (arXiv)", "F1 (arXiv)", "Цитирований", "Контракт ✓"],
                [_graph_row(c) for c in cases],
            ))
            lines.append("")

        if "layer2" in ref_data:
            data, rel = ref_data["layer2"]
            cases = _iter_cases(data)
            lines.append("### 1.3 Семантика (методы и датасеты)\n")
            lines.append(
                "Precision / Recall по методам и датасетам, упомянутым в статье.\n"
            )
            lines.append(_md_table(
                ["Статья", "Методы P", "Методы R", "Датасеты P", "Датасеты R", "✓"],
                [_layer2_row(c) for c in cases],
            ))
            lines.append("")

    # ── 2. Nightly: Layer-1 ───────────────────────────────────────────────────
    l1_rel = auth.get("layer1_nightly")
    if l1_rel:
        path = ROOT / str(l1_rel)
        if path.is_file():
            data = _read(path)
            cases = _iter_cases(data)
            lines.append("---\n")
            lines.append("## 2. Nightly — извлечение метаданных (Layer-1)\n")
            lines.append(
                f"**{len(cases)} статей** по детекции объектов (реальные PDF → Markdown).  \n"
                "Измеряем: точность заголовка, F1 arXiv-ссылок в библиографии, "
                "соответствие числа ссылок эталону.\n"
            )
            lines.append(_md_table(
                _layer1_headers(show_authors=False),
                [_layer1_row(c, show_authors=False) for c in cases],
            ))
            lines.append(_layer1_summary(cases) + "\n")
            lines.append(
                "> **Авторы F1** не показан: артефакт создан до разметки gold-авторов. "
                "После перепрогона nightly suite столбец появится с реальными значениями "
                "(все 30 nightly кейсов теперь содержат эталон авторов).\n"
            )
            lines.append("")

    # ── 3. Nightly: Layer-2 ───────────────────────────────────────────────────
    l2_rel = auth.get("layer2_nightly")
    if l2_rel:
        path = ROOT / str(l2_rel)
        if path.is_file():
            data = _read(path)
            cases = _iter_cases(data)
            lines.append("---\n")
            lines.append("## 3. Nightly — семантика (Layer-2)\n")
            lines.append(
                f"**{len(cases)} статей**. Precision/Recall по методам и датасетам, "
                "упомянутым в статье.\n"
            )
            lines.append(_md_table(
                ["Статья", "Методы P", "Методы R", "Датасеты P", "Датасеты R", "✓"],
                [_layer2_row(c) for c in cases],
            ))
            lines.append(_layer2_summary(cases) + "\n")
            lines.append("")

    # ── 4. Поиск по корпусу (Retrieval) ──────────────────────────────────────
    retrieval_keys = [
        ("Контрактные проверки (mock)", "retrieval_merge_safe_mock"),
        ("Строгий пилот (mock)", "retrieval_strict_pilot_mock"),
        ("Живой корпус (mini)", "retrieval_live_corpus_mini"),
    ]
    retrieval_sections: list[tuple[str, str, list[dict[str, Any]]]] = []
    for label, key in retrieval_keys:
        rel = auth.get(key)
        if not rel:
            continue
        path = ROOT / str(rel)
        if path.is_file():
            retrieval_sections.append((label, rel, _iter_cases(_read(path))))

    if retrieval_sections:
        lines.append("---\n")
        lines.append("## 4. Поиск по корпусу (Retrieval)\n")
        lines.append("Тестирование поиска по индексированному корпусу статей.\n")
        for label, rel, cases in retrieval_sections:
            all_mock = all(
                (c.get("metrics") or {}).get("contract_only") is True for c in cases
            )
            passed_n = _count_passed(cases, "passed")
            n = len(cases)
            if all_mock:
                lines.append(f"**{label}:** {passed_n}/{n} запросов пройдено (контракт-only).\n")
            else:
                lines.append(f"### {label}\n")
                rows: list[list[str]] = []
                for c in cases:
                    m = c.get("metrics") or {}
                    rows.append([
                        c.get("case_id", ""),
                        str(m.get("hit_count") if m.get("hit_count") is not None else "—"),
                        str(m.get("min_hit_count") if m.get("min_hit_count") is not None else "—"),
                        _tick(m.get("hit_ok")),
                        _tick(m.get("passed")),
                    ])
                lines.append(_md_table(
                    ["Запрос", "Найдено документов", "Минимум", "Найдено ✓", "Прошёл ✓"],
                    rows,
                ))
                lines.append("")

    # ── 5. Извлечение утверждений (Claims) ────────────────────────────────────
    claims_keys = [
        ("Контракт", "claims_merge_contract"),
        ("Mini (5 кейсов)", "claims_mini_suite"),
        ("Corpus v2 mini (5 кейсов)", "claims_corpus_v2_mini_suite"),
        ("Pilot (10 кейсов)", "claims_pilot_suite"),
    ]
    claims_sections: list[tuple[str, str, list[dict[str, Any]]]] = []
    for label, key in claims_keys:
        rel = auth.get(key)
        if not rel:
            continue
        path = ROOT / str(rel)
        if path.is_file():
            claims_sections.append((label, rel, _iter_cases(_read(path))))

    if claims_sections:
        lines.append("---\n")
        lines.append("## 5. Извлечение утверждений (Claims)\n")
        lines.append(
            "Precision/Recall по scientific claims, извлекаемым из текста статьи.  \n"
            "F1 = 1.00 — точное совпадение всех ожидаемых утверждений.\n"
        )
        for label, rel, cases in claims_sections:
            passed_n = _count_passed(cases, "passed")
            n = len(cases)
            rc_vals = _collect(cases, "claim_recall")
            pr_vals = _collect(cases, "claim_precision")
            if passed_n == n:
                lines.append(
                    f"**{label}:** {passed_n}/{n} ✓ · "
                    f"полнота = **{_mean_str(rc_vals)}** · "
                    f"точность = **{_mean_str(pr_vals)}**\n"
                )
            else:
                lines.append(f"### {label}\n")
                lines.append(_md_table(
                    ["Кейс", "Эталон (N)", "Полнота", "Точность", "✓"],
                    [_claims_row(c) for c in cases],
                ))
                lines.append("")

    # ── 6. Разрешение ссылок (References Resolution) ─────────────────────────
    refs_res_keys = [
        ("Контракт", "references_resolution_contract"),
        ("Mini", "references_resolution_mini"),
    ]
    refs_res_sections: list[tuple[str, str, list[dict[str, Any]]]] = []
    for label, key in refs_res_keys:
        rel = auth.get(key)
        if not rel:
            continue
        path = ROOT / str(rel)
        if path.is_file():
            refs_res_sections.append((label, rel, _iter_cases(_read(path))))

    if refs_res_sections:
        lines.append("---\n")
        lines.append("## 6. Разрешение ссылок (References Resolution)\n")
        lines.append(
            "Сопоставление raw-строк ссылок с идентификаторами работ (arXiv ID, DOI).\n"
        )
        for label, rel, cases in refs_res_sections:
            passed_n = _count_passed(cases, "passed")
            n = len(cases)
            rc_vals = _collect(cases, "resolution_recall")
            pr_vals = _collect(cases, "resolution_precision")
            if passed_n == n and n == 1:
                lines.append(
                    f"**{label}:** {passed_n}/{n} ✓ · "
                    f"полнота = **{_mean_str(rc_vals)}** · "
                    f"точность = **{_mean_str(pr_vals)}**\n"
                )
            else:
                lines.append(f"### {label}\n")
                lines.append(_md_table(
                    ["Тест", "Совпадений (эталон)", "Полнота", "Точность", "✓"],
                    [_refs_res_row(c) for c in cases],
                ))
                lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
