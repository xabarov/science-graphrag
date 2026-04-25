#!/usr/bin/env python3
"""Phase 6.E driver — run a single model pass over all currently-high-priority packs.

Reads existing ``consistency_report.json`` files, picks packs with
``spot_check_priority == "high"``, then invokes ``dual_extract_validate.py`` once
per pack with the requested ``--report-name`` (e.g. ``consistency_report.kimi.json``).

Skips packs that already have the per-model report unless ``--force`` is set.
Designed to be re-runnable: the script is a thin shell over the existing CLI so
all token / matcher / embedding settings live in one place.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


# Layer name → fixtures subdirectory and how to derive the layer flag for the CLI.
LAYER_DIRS = {
    "claims_v2": ("claims", "claims_v2"),
    "concept_topic_v2": ("concept_topic", "concept_topic_v2"),
    "contradictions_v1": ("contradictions_v1", "contradictions_v1"),
    "idea_assist_live": ("idea_assist_v1", "idea_assist_live"),
    "workspace_scoped_live": ("retrieval/workspace_scoped_live", "workspace_scoped_live"),
    "hybrid_ablation_v2": ("retrieval/hybrid_ablation_v2", "hybrid_ablation_v2"),
    "multihop_v2": ("retrieval/multihop_v2", "multihop_v2"),
    "agent_tools_live": ("agent_tools_v1", "agent_tools_live"),
}


def _find_high_priority_packs(fixtures_root: Path) -> dict[str, list[Path]]:
    """Return {layer_name: [pack_dir, ...]} for packs with consensus priority high."""

    result: dict[str, list[Path]] = defaultdict(list)
    for layer, (sub, _flag) in LAYER_DIRS.items():
        base = fixtures_root / sub
        if not base.exists():
            continue
        if layer.startswith("dedup_"):
            continue
        # The dedup layers store gold inside <type>s_v1/ but we exclude them
        # from Phase 6.E since they are already 100% promoted.
        for pack in sorted(base.iterdir()):
            if not pack.is_dir():
                continue
            report = pack / "consistency_report.json"
            if not report.exists():
                continue
            try:
                d = json.loads(report.read_text(encoding="utf-8"))
            except Exception:  # pylint: disable=broad-except
                continue
            if d.get("spot_check_priority") == "high":
                if layer == "agent_tools_live" and not pack.name.startswith("live_"):
                    continue
                result[layer].append(pack)
    return result


def _cli_invocation(
    *,
    pack: Path,
    layer_flag: str,
    model: str,
    report_name: str,
    max_output_tokens: int,
    with_embeddings: bool,
    reasoning_mode: str,
) -> list[str]:
    cmd = [
        str(ROOT / ".venv/bin/python"),
        str(ROOT / "scripts/dual_extract_validate.py"),
        "--layer",
        layer_flag,
        "--pack",
        str(pack),
        "--model",
        model,
        "--report-name",
        report_name,
        "--max-output-tokens",
        str(max_output_tokens),
        "--save-raw-response",
        "--reasoning-mode",
        reasoning_mode,
    ]
    if with_embeddings:
        cmd.append("--with-embeddings")
    return cmd


def main() -> int:
    p = argparse.ArgumentParser(
        description="Phase 6.E driver: model pass over high-priority packs."
    )
    p.add_argument("--model", required=True, help="LLM model id, e.g. moonshotai/kimi-k2.6.")
    p.add_argument(
        "--tag",
        required=True,
        help="Short tag for output files (e.g. 'kimi'). Reports will be saved as "
        "'consistency_report.<tag>.json'.",
    )
    p.add_argument("--max-output-tokens", type=int, default=8192)
    p.add_argument(
        "--with-embeddings",
        action="store_true",
        help="Pass --with-embeddings to the underlying CLI (only relevant for layers "
        "with embedding-cascade matchers, currently claims_v2/contradictions_v1).",
    )
    p.add_argument(
        "--fixtures-root",
        type=Path,
        default=ROOT / "tests/fixtures/benchmarks",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Re-run even if the per-tag report already exists.",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process at most N packs total (across layers). Useful for smoke runs.",
    )
    p.add_argument(
        "--layers",
        nargs="+",
        default=None,
        help="Restrict to listed layers (default: all).",
    )
    p.add_argument(
        "--log-output",
        type=Path,
        default=None,
        help="Append per-pack log (one JSON line) to this file.",
    )
    p.add_argument(
        "--reasoning-mode",
        choices=("auto", "disabled", "low", "medium", "high"),
        default="auto",
        help=(
            "Forwarded to the underlying CLI. Use 'disabled' for moonshotai/kimi-k2.6 "
            "to suppress hidden CoT and prevent JSON truncation."
        ),
    )
    p.add_argument(
        "--parallel",
        type=int,
        default=1,
        help=(
            "Run up to N packs concurrently via subprocess. Useful for slow reasoning "
            "models (e.g. kimi-k2.6 ~5min/pack). Default 1 (serial)."
        ),
    )
    args = p.parse_args()

    found = _find_high_priority_packs(args.fixtures_root)
    if args.layers:
        found = {k: v for k, v in found.items() if k in set(args.layers)}
    if not found:
        print("no high-priority packs to process", file=sys.stderr)
        return 1

    report_name = f"consistency_report.{args.tag}.json"
    plan: list[tuple[str, Path]] = []
    for layer, packs in found.items():
        for pack in packs:
            if not args.force and (pack / report_name).exists():
                continue
            plan.append((layer, pack))
            if args.limit is not None and len(plan) >= args.limit:
                break
        if args.limit is not None and len(plan) >= args.limit:
            break

    if not plan:
        print("nothing to do (every pack already has the per-tag report)", file=sys.stderr)
        return 0

    print(
        f"Phase 6.E pass: model={args.model} tag={args.tag} "
        f"packs={len(plan)} max_tokens={args.max_output_tokens}",
        file=sys.stderr,
    )

    log_handle = args.log_output.open("a", encoding="utf-8") if args.log_output else None
    log_lock = threading.Lock()

    def _run_one(idx: int, layer: str, pack: Path) -> dict:
        layer_flag = LAYER_DIRS[layer][1]
        cmd = _cli_invocation(
            pack=pack,
            layer_flag=layer_flag,
            model=args.model,
            report_name=report_name,
            max_output_tokens=args.max_output_tokens,
            with_embeddings=args.with_embeddings,
            reasoning_mode=args.reasoning_mode,
        )
        t0 = time.perf_counter()
        with log_lock:
            print(
                f"[{idx}/{len(plan)}] {layer}/{pack.name}: starting",
                file=sys.stderr,
                flush=True,
            )
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            text=True,
        )
        dt = time.perf_counter() - t0
        ok = proc.returncode == 0 and (pack / report_name).exists()
        with log_lock:
            print(
                f"[{idx}/{len(plan)}] {layer}/{pack.name}: done in {dt:.1f}s, "
                f"ok={ok}, rc={proc.returncode}",
                file=sys.stderr,
                flush=True,
            )
            if not ok:
                tail = "\n".join(proc.stderr.strip().splitlines()[-6:])
                print(f"  STDERR tail:\n{tail}", file=sys.stderr, flush=True)
            if log_handle is not None:
                log_handle.write(
                    json.dumps(
                        {
                            "layer": layer,
                            "pack": pack.name,
                            "model": args.model,
                            "tag": args.tag,
                            "elapsed_s": round(dt, 1),
                            "rc": proc.returncode,
                            "ok": ok,
                        }
                    )
                    + "\n"
                )
                log_handle.flush()
        return {"layer": layer, "pack": pack.name, "ok": ok, "elapsed_s": dt}

    try:
        if args.parallel <= 1:
            for idx, (layer, pack) in enumerate(plan, start=1):
                _run_one(idx, layer, pack)
        else:
            # Subprocess-based parallelism: each worker call sits on its own HTTPS
            # socket so the GIL is irrelevant; the only contention point is logging,
            # guarded by ``log_lock`` above.
            with ThreadPoolExecutor(max_workers=args.parallel) as pool:
                futures = [
                    pool.submit(_run_one, idx, layer, pack)
                    for idx, (layer, pack) in enumerate(plan, start=1)
                ]
                for fut in as_completed(futures):
                    fut.result()
    finally:
        if log_handle is not None:
            log_handle.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
