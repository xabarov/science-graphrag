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
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUMMARY = ROOT / "eval/results/benchmark-metrics-summary.json"
DEFAULT_OUT = ROOT / "docs/benchmarks/benchmark-metrics-values.md"


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _fmt(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        if isinstance(v, float) and math.isnan(v):
            return "NaN"
        s = f"{float(v):.6f}"
        s = s.rstrip("0").rstrip(".")
        return s or "0"
    return str(v)


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out) + "\n"


def _iter_cases(data: dict[str, Any]) -> list[dict[str, Any]]:
    if "cases" in data:
        return list(data["cases"])
    if "case" in data:
        return [data["case"]]
    return []


def _layer1_row(case: dict[str, Any]) -> list[str]:
    m = case.get("metrics") or {}
    md = m.get("metadata") or {}
    au = m.get("authorships") or {}
    rf = m.get("references") or {}
    ct = m.get("contract") or {}
    return [
        case.get("case_id", ""),
        _fmt(ct.get("passed")),
        _fmt(md.get("title_exact_normalized")),
        _fmt(md.get("title_rouge_l")),
        _fmt(md.get("title_token_f1")),
        _fmt(md.get("abstract_rouge_l_vs_prefix")),
        _fmt(au.get("names_f1")),
        _fmt(au.get("affiliations_f1")),
        _fmt(rf.get("sample_arxiv_f1")),
        _fmt(rf.get("sample_doi_f1")),
        _fmt(rf.get("count_ok")),
    ]


def _graph_row(case: dict[str, Any]) -> list[str]:
    m = case.get("metrics") or {}
    ct = m.get("contract") or {}
    return [
        case.get("case_id", ""),
        _fmt(m.get("has_expectations")),
        _fmt(ct.get("passed")),
        _fmt(m.get("cited_arxiv_precision")),
        _fmt(m.get("cited_arxiv_recall")),
        _fmt(m.get("cited_arxiv_f1")),
        _fmt((m.get("snapshot") or {}).get("cites_count")),
    ]


def _layer2_row(case: dict[str, Any]) -> list[str]:
    m = case.get("metrics") or {}
    rm = m.get("recall_methods_num")
    rd = m.get("recall_methods_denom")
    rdn = m.get("recall_datasets_num")
    rdd = m.get("recall_datasets_denom")
    r_frac_m = f"{rm}/{rd}" if rd not in (None, 0) else ""
    r_frac_d = f"{rdn}/{rdd}" if rdd not in (None, 0) else ""
    return [
        case.get("case_id", ""),
        _fmt(m.get("passed")),
        _fmt(m.get("precision_methods")),
        r_frac_m,
        _fmt(m.get("precision_datasets")),
        r_frac_d,
        _fmt(m.get("notes")),
    ]


def _retrieval_row(case: dict[str, Any]) -> list[str]:
    m = case.get("metrics") or {}
    return [
        case.get("case_id", ""),
        _fmt(m.get("passed")),
        _fmt(m.get("contract_only")),
        _fmt(m.get("hit_count")),
        _fmt(m.get("hit_ok")),
        _fmt(m.get("min_hit_count")),
        _fmt(m.get("work_id_ok")),
    ]


def _claims_row(case: dict[str, Any]) -> list[str]:
    m = case.get("metrics") or {}
    return [
        case.get("case_id", ""),
        _fmt(m.get("passed")),
        _fmt(m.get("claim_recall")),
        _fmt(m.get("claim_precision")),
        _fmt(m.get("expected_count")),
        _fmt(m.get("predicted_count")),
    ]


def _refs_res_row(case: dict[str, Any]) -> list[str]:
    m = case.get("metrics") or {}
    return [
        case.get("case_id", ""),
        _fmt(m.get("passed")),
        _fmt(m.get("resolution_recall")),
        _fmt(m.get("resolution_precision")),
        _fmt(m.get("expected_count")),
        _fmt(m.get("predicted_count")),
    ]


def _mean(xs: list[float]) -> str:
    if not xs:
        return ""
    return _fmt(statistics.mean(xs))


def _aggregate_names_f1(cases: list[dict[str, Any]]) -> tuple[str, int]:
    vals: list[float] = []
    for c in cases:
        au = (c.get("metrics") or {}).get("authorships") or {}
        if int(au.get("gold_count") or 0) > 0:
            try:
                vals.append(float(au.get("names_f1", 0.0)))
            except (TypeError, ValueError):
                pass
    return _mean(vals), len(vals)


def _mean_float_cases(
    cases: list[dict[str, Any]],
    getter: Callable[[dict[str, Any]], Any],
) -> tuple[str, int]:
    vals: list[float] = []
    for c in cases:
        raw = getter(c)
        if raw is None or raw == "":
            continue
        try:
            vals.append(float(raw))
        except (TypeError, ValueError):
            continue
    return (_mean(vals), len(vals)) if vals else ("", 0)


def _layer1_nightly_aggregate_rows(  # pylint: disable=too-many-locals
    cases: list[dict[str, Any]],
) -> list[list[str]]:
    """Per-field suite-level stats for layer-1 nightly JSON (one row per signal)."""

    n = len(cases)
    if not n:
        return []

    def meta_get(c: dict[str, Any], key: str) -> Any:
        return (c.get("metrics") or {}).get("metadata", {}).get(key)

    title_true = sum(1 for c in cases if meta_get(c, "title_exact_normalized") is True)
    contract_true = sum(
        1 for c in cases if (c.get("metrics") or {}).get("contract", {}).get("passed") is True
    )
    ref_ok = sum(
        1 for c in cases if (c.get("metrics") or {}).get("references", {}).get("count_ok") is True
    )

    names_vals: list[float] = []
    aff_vals: list[float] = []
    for c in cases:
        au = (c.get("metrics") or {}).get("authorships") or {}
        if int(au.get("gold_count") or 0) <= 0:
            continue
        try:
            names_vals.append(float(au.get("names_f1", 0.0)))
            aff_vals.append(float(au.get("affiliations_f1", 0.0)))
        except (TypeError, ValueError):
            continue

    arxiv_m, arxiv_n = _mean_float_cases(
        cases, lambda c: (c.get("metrics") or {}).get("references", {}).get("sample_arxiv_f1")
    )
    doi_m, doi_n = _mean_float_cases(
        cases, lambda c: (c.get("metrics") or {}).get("references", {}).get("sample_doi_f1")
    )
    tr_m, tr_n = _mean_float_cases(cases, lambda c: meta_get(c, "title_rouge_l"))
    tt_m, tt_n = _mean_float_cases(cases, lambda c: meta_get(c, "title_token_f1"))
    ar_m, ar_n = _mean_float_cases(cases, lambda c: meta_get(c, "abstract_rouge_l_vs_prefix"))

    def pct_fmt(num: int) -> str:
        return f"{100.0 * num / n:.1f}%"

    rows: list[list[str]] = [
        ["`contract.passed`", str(n), pct_fmt(contract_true), "доля кейсов с passed"],
        ["`title_exact_normalized`", str(n), pct_fmt(title_true), "доля exact title"],
        ["`references.count_ok`", str(n), pct_fmt(ref_ok), "доля кейсов с count_ok"],
    ]
    if names_vals:
        rows.append(
            [
                "`names_f1` (mean)",
                str(len(names_vals)),
                _fmt(statistics.mean(names_vals)),
                "только `gold_count`>0 в authorships",
            ]
        )
    else:
        rows.append(["`names_f1` (mean)", "0", "", "нет эталона авторов в отчёте"])
    if aff_vals:
        rows.append(
            [
                "`affiliations_f1` (mean)",
                str(len(aff_vals)),
                _fmt(statistics.mean(aff_vals)),
                "только при `gold_count`>0",
            ]
        )
    else:
        rows.append(["`affiliations_f1` (mean)", "0", "", "нет эталона аффилиаций"])
    rows.append(
        [
            "`sample_arxiv_f1` (mean)",
            str(arxiv_n),
            arxiv_m,
            "по кейсам где значение есть в JSON",
        ]
    )
    rows.append(
        [
            "`sample_doi_f1` (mean)",
            str(doi_n),
            doi_m,
            "по кейсам где значение есть в JSON",
        ]
    )
    rows.append(
        [
            "`title_rouge_l` (mean)",
            str(tr_n),
            tr_m,
            "если ключ есть в metadata",
        ]
    )
    rows.append(
        [
            "`title_token_f1` (mean)",
            str(tt_n),
            tt_m,
            "если ключ есть в metadata",
        ]
    )
    rows.append(
        [
            "`abstract_rouge_l_vs_prefix` (mean)",
            str(ar_n),
            ar_m,
            "если ключ есть в metadata",
        ]
    )
    return rows


def main() -> None:  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    """Read ``benchmark-metrics-summary.json`` and emit markdown metric tables."""
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
    lines: list[str] = []

    gen_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines.append("# Таблицы значений метрик (снимок артефактов)\n")
    rel_summary = summary_path.relative_to(ROOT)
    lines.append(
        f"Этот файл **генерируется** из JSON в `eval/results/`, перечисленных в "
        f"`{rel_summary}` → `authoritative_artifacts`. "
        "Не правьте таблицы вручную: при обновлении отчётов перегенерируйте файл.\n"
    )
    lines.append("```bash\n.venv/bin/python scripts/generate_benchmark_metrics_tables.py\n```\n")
    lines.append(f"**Сгенерировано:** {gen_at}\n")
    lines.append("## Что означает `passed`\n")
    lines.append(
        "- **Layer-1:** `metrics.contract.passed` — все пороговые проверки эталона для кейса.\n"
        "- **Graph:** `metrics.contract.passed` при наличии `graph_expectations`.\n"
        "- **Layer-2 semantic:** `metrics.passed` — пороги recall/precision по методам "
        "и датасетам.\n"
        "- **Retrieval / claims / references_resolution:** см. `eval/*/metrics.py` и поля `passed` "
        "в JSON.\n"
    )
    lines.append(
        "Сводка gate без числовых колонок: "
        "[benchmark-metrics-summary.md](../../eval/results/benchmark-metrics-summary.md). "
        "Смысл метрик: [benchmark-metrics-catalog.md](benchmark-metrics-catalog.md).\n"
    )

    # Optional gate extras from summary
    l1n = summary.get("layer1_nightly") or {}
    if l1n:
        lines.append("## Сводные сигналы из `benchmark-metrics-summary.json`\n")
        rows = [
            ["`decision`", _fmt((summary.get("decision_gate") or {}).get("decision"))],
            ["layer1 nightly `failed_count`", _fmt(l1n.get("failed_count"))],
            [
                "layer1 nightly `references_llm_failed_events`",
                _fmt(l1n.get("references_llm_failed_events")),
            ],
        ]
        l2n = summary.get("layer2_nightly") or {}
        if l2n:
            rows.append(["layer2 nightly `failed_count`", _fmt(l2n.get("failed_count"))])
        lines.append(_md_table(["Поле", "Значение"], rows))
        lines.append("")

    ref_paths = auth.get("reference") or []
    for label, rel in zip(
        [
            "Layer-1 reference (yolov1)",
            "Graph reference (yolov1)",
            "Layer-2 reference (yolov1_semantic)",
        ],
        ref_paths,
    ):
        path = ROOT / rel
        if not path.is_file():
            continue
        data = _read(path)
        cases = _iter_cases(data)
        lines.append(f"## {label}\n")
        lines.append(f"Артефакт: `{rel}`\n")
        if "layer2" in rel or "semantic" in rel:
            hdr = [
                "case_id",
                "passed",
                "precision_methods",
                "recall_methods",
                "precision_datasets",
                "recall_datasets",
                "notes",
            ]
            body = [_layer2_row(c) for c in cases]
        elif "graph" in rel:
            hdr = [
                "case_id",
                "has_expectations",
                "contract_passed",
                "cited_arxiv_P",
                "cited_arxiv_R",
                "cited_arxiv_F1",
                "cites_count",
            ]
            body = [_graph_row(c) for c in cases]
        else:
            hdr = [
                "case_id",
                "contract_passed",
                "title_exact",
                "title_rouge_L",
                "title_token_F1",
                "abstract_rouge_L_vs_prefix",
                "names_F1",
                "affiliations_F1",
                "sample_arxiv_F1",
                "sample_doi_F1",
                "ref_count_ok",
            ]
            body = [_layer1_row(c) for c in cases]
        lines.append(_md_table(hdr, body))
        lines.append("")

    l1_rel = auth.get("layer1_nightly")
    if l1_rel:
        path = ROOT / str(l1_rel)
        if path.is_file():
            data = _read(path)
            cases = _iter_cases(data)
            lines.append("## Layer-1 nightly (`nightly_heavy`)\n")
            lines.append(f"Артефакт: `{l1_rel}`\n")
            summ = data.get("summary") or {}
            lines.append("### Общие цифры (верх suite-JSON)\n")
            lines.append(
                "| Поле | Значение |\n| --- | --- |\n"
                f"| `summary.case_count` | {_fmt(summ.get('case_count'))} |\n"
                f"| `summary.all_passed` | {_fmt(summ.get('all_passed'))} |\n"
            )
            lines.append(
                "Пороговый gate и счётчики (`failed_count`, `references_llm_failed_events`) — в "
                "`eval/results/benchmark-metrics-summary.json` "
                "(секции `layer1_nightly`, `decision_gate`). Усреднённых F1/ROUGE по suite там "
                "**нет**: сводка только про прохождение контракта.\n"
            )
            hdr = [
                "case_id",
                "contract_passed",
                "title_exact",
                "title_rouge_L",
                "title_token_F1",
                "abstract_rouge_L_vs_prefix",
                "names_F1",
                "aff_F1",
                "sample_arxiv_F1",
                "sample_doi_F1",
                "ref_count_ok",
            ]
            body = [_layer1_row(c) for c in cases]
            lines.append(_md_table(hdr, body))
            agg_rows = _layer1_nightly_aggregate_rows(cases)
            if agg_rows:
                lines.append("### Агрегаты по полям (nightly suite)\n")
                lines.append(
                    _md_table(
                        ["Поле", "N (с сигналом)", "Среднее / доля", "Комментарий"],
                        agg_rows,
                    )
                )
                lines.append("")
            mean_nf, n = _aggregate_names_f1(cases)
            if n:
                note = (
                    f"*Среднее `names_F1` по кейсам с `authorships.gold_count` > 0: "
                    f"**{mean_nf}** (n={n}).*\n"
                )
                lines.append(note)
            else:
                lines.append(
                    "*Среднее `names_F1` по кейсам с непустым эталоном авторов: **n/a**. "
                    "В текущем nightly JSON у всех кейсов `gold_count` = 0 в блоке authorships — "
                    "колонка `names_F1` не используется как сигнал по корпусу.*\n"
                )
            lines.append("### Почему много нулей и пустых ячеек в таблице ниже\n")
            lines.append(
                "- **`names_F1` почти везде 0:** в `gold.json` многих `*_realpdf` кейсов список "
                "`authorships` **намеренно пустой** (см. `description` в gold: авторская строка "
                "не размечена как comma-separated). Тогда эталон имён — пустое множество, а "
                "предсказанные авторы считаются ложноположительными → precision/recall/F1 по "
                "именам = 0 (см. `eval/layer1/metrics.py`, `prf1_tp_fp_fn`). Это **не** значит, "
                "что модель «не извлекла авторов» в смысле продукта — значит, что **бенчмарк "
                "пока не ставит эталон по авторам** на этом корпусе.\n"
            )
            lines.append(
                "- **`aff_F1` часто 0 по той же причине** (пустой эталон аффилиаций); единичные "
                "ненули — там, где в gold всё же заданы аффилиации / совпали множества.\n"
            )
            lines.append(
                "- **Пустые `title_rouge_L` / `title_token_F1` / `abstract_rouge_L_vs_prefix`:** "
                "в закоммиченном JSON этих ключей в `metrics.metadata` часто **нет** "
                "(таблица показывает пусто). В актуальном коде `eval/layer1/metrics.py` поля "
                "считаются и при сериализации обычно были бы `null` или число; если нужны "
                "ROUGE-цифры в отчёте — **перепрогоните** suite и обновите артефакт, либо "
                "смотрите кейсы с непустым эталоном заголовка/абстракта (например merge_safe).\n"
            )
            lines.append(
                "- **Что реально драйвит `contract_passed` на nightly:** в типичном `gold.json` "
                "для realpdf заданы `title` + `abstract_prefix` + ограничения по числу ссылок "
                "(`references.expected_count` / `min_count`), а `quality_thresholds` часто "
                "`null` — т.е. **нет** порогов по `min_title_rouge_l` / F1 авторам в контракте.\n"
            )
            lines.append("")

    l2_rel = auth.get("layer2_nightly")
    if l2_rel:
        path = ROOT / str(l2_rel)
        if path.is_file():
            data = _read(path)
            cases = _iter_cases(data)
            lines.append("## Layer-2 nightly (`nightly_semantic`)\n")
            lines.append(f"Артефакт: `{l2_rel}`\n")
            summ2 = data.get("summary") or {}
            lines.append("### Общие цифры (верх suite-JSON)\n")
            lines.append(
                "| Поле | Значение |\n| --- | --- |\n"
                f"| `summary.case_count` | {_fmt(summ2.get('case_count'))} |\n"
                f"| `summary.all_passed` | {_fmt(summ2.get('all_passed'))} |\n"
            )
            lines.append("")
            hdr = [
                "case_id",
                "passed",
                "P_methods",
                "R_methods",
                "P_datasets",
                "R_datasets",
                "notes",
            ]
            body = [_layer2_row(c) for c in cases]
            lines.append(_md_table(hdr, body))
            lines.append("")

    retrieval_keys = [
        ("Retrieval merge_safe_contract (mock)", "retrieval_merge_safe_mock"),
        ("Retrieval strict_pilot (mock)", "retrieval_strict_pilot_mock"),
        ("Retrieval live_corpus_mini", "retrieval_live_corpus_mini"),
    ]
    for title, key in retrieval_keys:
        rel = auth.get(key)
        if not rel:
            continue
        path = ROOT / str(rel)
        if not path.is_file():
            continue
        data = _read(path)
        cases = _iter_cases(data)
        lines.append(f"## {title}\n")
        lines.append(f"Артефакт: `{rel}`\n")
        hdr = [
            "case_id",
            "passed",
            "contract_only",
            "hit_count",
            "hit_ok",
            "min_hit_count",
            "work_id_ok",
        ]
        body = [_retrieval_row(c) for c in cases]
        lines.append(_md_table(hdr, body))
        lines.append("")

    claims_keys = [
        ("Claims merge_contract", "claims_merge_contract"),
        ("Claims mini", "claims_mini_suite"),
        ("Claims corpus_v2_mini", "claims_corpus_v2_mini_suite"),
        ("Claims pilot", "claims_pilot_suite"),
    ]
    for title, key in claims_keys:
        rel = auth.get(key)
        if not rel:
            continue
        path = ROOT / str(rel)
        if not path.is_file():
            continue
        data = _read(path)
        cases = _iter_cases(data)
        lines.append(f"## {title}\n")
        lines.append(f"Артефакт: `{rel}`\n")
        hdr = ["case_id", "passed", "claim_recall", "claim_precision", "expected_n", "predicted_n"]
        body = [_claims_row(c) for c in cases]
        lines.append(_md_table(hdr, body))
        lines.append("")

    for title, key in [
        ("References resolution contract", "references_resolution_contract"),
        ("References resolution mini", "references_resolution_mini"),
    ]:
        rel = auth.get(key)
        if not rel:
            continue
        path = ROOT / str(rel)
        if not path.is_file():
            continue
        data = _read(path)
        cases = _iter_cases(data)
        lines.append(f"## {title}\n")
        lines.append(f"Артефакт: `{rel}`\n")
        hdr = ["case_id", "passed", "resolution_R", "resolution_P", "expected_n", "predicted_n"]
        body = [_refs_res_row(c) for c in cases]
        lines.append(_md_table(hdr, body))
        lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
