"""Compare agent_note OFF vs ON benchmark artifacts.

This utility expects two suite JSON artifacts with ``cases`` lists where each case
contains ``duration_ms`` and (optionally) ``run_metadata.usage.total_tokens``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import median
from typing import Any


def _load_cases(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = data.get("cases")
    if not isinstance(cases, list):
        return []
    return [c for c in cases if isinstance(c, dict)]


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    arr = sorted(values)
    idx = max(0, int(round(0.95 * (len(arr) - 1))))
    return float(arr[idx])


def _extract_latency(cases: list[dict[str, Any]]) -> list[float]:
    out: list[float] = []
    for case in cases:
        raw = case.get("duration_ms")
        try:
            out.append(float(raw or 0.0))
        except (TypeError, ValueError):
            out.append(0.0)
    return out


def _extract_tokens(cases: list[dict[str, Any]]) -> list[float]:
    out: list[float] = []
    for case in cases:
        usage = (
            (case.get("run_metadata") or {}).get("usage")
            if isinstance(case.get("run_metadata"), dict)
            else None
        )
        raw = usage.get("total_tokens") if isinstance(usage, dict) else None
        try:
            out.append(float(raw or 0.0))
        except (TypeError, ValueError):
            out.append(0.0)
    return out


def _summary(cases: list[dict[str, Any]]) -> dict[str, Any]:
    lat = _extract_latency(cases)
    tok = _extract_tokens(cases)
    return {
        "count": len(cases),
        "latency_p50_ms": round(float(median(lat)) if lat else 0.0, 2),
        "latency_p95_ms": round(_p95(lat), 2),
        "tokens_p50": round(float(median(tok)) if tok else 0.0, 2),
        "tokens_p95": round(_p95(tok), 2),
        "tokens_available_rate": round(
            (sum(1 for x in tok if x > 0) / len(tok)) if tok else 0.0,
            4,
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--off-json", type=Path, required=True)
    parser.add_argument("--on-json", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    args = parser.parse_args()

    off_cases = _load_cases(args.off_json)
    on_cases = _load_cases(args.on_json)
    if not off_cases or not on_cases:
        raise SystemExit("Both artifacts must contain non-empty `cases` arrays.")

    if len(off_cases) != len(on_cases):
        raise SystemExit("Artifacts must be aligned: same number of cases.")

    off = _summary(off_cases)
    on = _summary(on_cases)
    delta = {
        "latency_p50_ms": round(on["latency_p50_ms"] - off["latency_p50_ms"], 2),
        "latency_p95_ms": round(on["latency_p95_ms"] - off["latency_p95_ms"], 2),
        "tokens_p50": round(on["tokens_p50"] - off["tokens_p50"], 2),
        "tokens_p95": round(on["tokens_p95"] - off["tokens_p95"], 2),
    }

    payload = {
        "off_artifact": str(args.off_json),
        "on_artifact": str(args.on_json),
        "off": off,
        "on": on,
        "delta_on_minus_off": delta,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.out_md.write_text(
        "\n".join(
            [
                "# Agent Note Cost Compare",
                "",
                f"- OFF artifact: `{args.off_json}`",
                f"- ON artifact: `{args.on_json}`",
                "",
                "## OFF",
                f"- count: `{off['count']}`",
                f"- latency p50/p95 ms: `{off['latency_p50_ms']}` / `{off['latency_p95_ms']}`",
                f"- tokens p50/p95: `{off['tokens_p50']}` / `{off['tokens_p95']}`",
                "",
                "## ON",
                f"- count: `{on['count']}`",
                f"- latency p50/p95 ms: `{on['latency_p50_ms']}` / `{on['latency_p95_ms']}`",
                f"- tokens p50/p95: `{on['tokens_p50']}` / `{on['tokens_p95']}`",
                "",
                "## Delta (ON - OFF)",
                f"- latency p50/p95 ms: `{delta['latency_p50_ms']}` / `{delta['latency_p95_ms']}`",
                f"- tokens p50/p95: `{delta['tokens_p50']}` / `{delta['tokens_p95']}`",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
