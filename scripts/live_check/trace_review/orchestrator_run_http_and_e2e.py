"""HTTP suite + optional E2E subprocess stages for trace-review."""

from __future__ import annotations

import tempfile
from argparse import Namespace
from pathlib import Path
from typing import Any

from .orchestrator_stage_runner import execute_trace_stage as _execute_trace_stage
from .orchestrator_subprocess import run_http_suite as _run_http_suite
from .orchestrator_subprocess import run_optional_e2e as _run_optional_e2e


def run_http_suite_trace_stage(
    args: Namespace,
    exec_stages: list[dict[str, Any]],
    *,
    hb_sec: float,
) -> list[dict[str, Any]]:
    """Run ``http_suite`` stage and return checks list."""
    return _execute_trace_stage(
        exec_stages,
        "http_suite",
        lambda: _run_http_suite(
            base_url=args.base_url.rstrip("/"),
            workspace_id=args.workspace_id,
            timeout=args.timeout,
            skip_sse=args.skip_sse,
            skip_multi_turn=args.skip_multi_turn,
            extended_safety=(args.suite == "acceptance"),
        ),
        heartbeat_interval_s=hb_sec,
    )


def run_e2e_trace_stage_with_report_path(
    args: Namespace,
    exec_stages: list[dict[str, Any]],
    *,
    hb_sec: float,
    e2e_subprocess_timeout_sec: float | int,
) -> tuple[Any, Path | None]:
    """Run optional E2E audit; return (e2e_blob, temp_report_json_path or None)."""
    report_json_path: Path | None = None
    if not args.skip_e2e:
        tmp = tempfile.NamedTemporaryFile(  # noqa: SIM115  # pylint: disable=consider-using-with
            suffix=".json",
            delete=False,
            prefix="e2e_full_report_",
        )
        tmp.close()
        report_json_path = Path(tmp.name)

    e2e = _execute_trace_stage(
        exec_stages,
        "e2e_audit_subprocess",
        lambda: _run_optional_e2e(
            args,
            report_json_path,
            subprocess_timeout=e2e_subprocess_timeout_sec,
        ),
        heartbeat_interval_s=hb_sec,
    )
    return e2e, report_json_path


__all__ = ["run_e2e_trace_stage_with_report_path", "run_http_suite_trace_stage"]
