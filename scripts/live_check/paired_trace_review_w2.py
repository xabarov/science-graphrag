#!/usr/bin/env python3
"""W2 wrapper: compare two trace-review-v1 artifacts with R4/R3 default latency horizon (+25%).

Delegates to ``trace_regression_compare`` with ``--max-latency-p95-regress-ratio 1.25`` and
matching warn ratio so operator latency verdict matches backlog W2 acceptance.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

# Horizon: candidate must not exceed baseline * 1.25 on latency_p95_ms (unless waived upstream).
_DEFAULT_W2_LATENCY_REGRESS_RATIO = 1.25


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    parser.add_argument(
        "--max-latency-p95-regress-ratio",
        type=float,
        default=_DEFAULT_W2_LATENCY_REGRESS_RATIO,
        help=(
            "Hard fail when both runs have latency_p95_ms and candidate > baseline * ratio "
            f"(default {_DEFAULT_W2_LATENCY_REGRESS_RATIO} = +25%%)."
        ),
    )
    parser.add_argument(
        "--latency-warn-ratio",
        type=float,
        default=_DEFAULT_W2_LATENCY_REGRESS_RATIO,
        help="Advisory WARN band when candidate exceeds baseline * ratio (default: same as fail).",
    )
    parser.add_argument(
        "--warn-is-pass",
        action="store_true",
        help="Forward to trace_regression_compare: WARN exits 0.",
    )
    parser.add_argument(
        "extra_args",
        nargs=argparse.REMAINDER,
        help="Additional flags passed through to trace_regression_compare (prefix with --).",
    )
    return parser


def main() -> int:
    """Run trace regression compare with W2 default latency ratio caps."""
    args = _build_parser().parse_args()
    for label, path in (("baseline", args.baseline), ("candidate", args.candidate)):
        if not path.is_file():
            print(f"[paired-w2] {label} path is not a file: {path}", file=sys.stderr, flush=True)
            return 2
    # Import after sys.path bootstrap (same pattern as trace_regression_compare.py).
    from trace_compare.runner import main as compare_main  # pylint: disable=import-outside-toplevel,import-error

    argv: list[str] = [
        "--baseline",
        str(args.baseline),
        "--candidate",
        str(args.candidate),
        "--out-json",
        str(args.out_json),
        "--out-md",
        str(args.out_md),
        "--max-latency-p95-regress-ratio",
        str(float(args.max_latency_p95_regress_ratio)),
        "--latency-warn-ratio",
        str(float(args.latency_warn_ratio)),
    ]
    if args.warn_is_pass:
        argv.append("--warn-is-pass")
    extra = list(args.extra_args or [])
    if extra and extra[0] == "--":
        extra = extra[1:]
    argv.extend(extra)
    return int(compare_main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
