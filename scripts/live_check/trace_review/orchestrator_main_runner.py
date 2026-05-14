"""Core execution path for ``agent_trace_review`` (split from entrypoint for size)."""

from __future__ import annotations

import sys
from argparse import Namespace
from typing import Any

from .orchestrator_env import e2e_subprocess_timeout_sec as _e2e_subprocess_timeout_sec
from .orchestrator_env import ensure_local_imports as _ensure_local_imports
from .orchestrator_env import load_dotenv as _load_dotenv
from .orchestrator_env import (
    trace_review_heartbeat_interval_s as _trace_review_heartbeat_interval_s,
)
from .orchestrator_run_artifacts import run_trace_review_artifact_phases_after_http_e2e
from .orchestrator_run_context import (
    apply_suite_and_profile_side_effects,
    preflight_acceptance_workspace,
)
from .orchestrator_run_http_and_e2e import (
    run_e2e_trace_stage_with_report_path,
    run_http_suite_trace_stage,
)


def run_agent_trace_review(args: Namespace) -> int:
    """Execute trace-review pipeline; mutates ``args`` for profile/suite side-effects."""
    _ensure_local_imports()
    from dotenv_util import (  # pylint: disable=import-outside-toplevel,import-error
        resolve_live_base_url,
    )

    _load_dotenv(args.env_file)
    args.base_url = resolve_live_base_url(args.base_url)
    apply_suite_and_profile_side_effects(args)
    early = preflight_acceptance_workspace(args)
    if early is not None:
        return early

    hb_sec = _trace_review_heartbeat_interval_s()
    exec_stages: list[dict[str, Any]] = []
    e2e_subprocess_timeout_sec = _e2e_subprocess_timeout_sec()
    print(
        f"[trace-review] run_start suite={args.suite} profile={args.profile} "
        f"heartbeat_sec={hb_sec} e2e_subprocess_timeout_sec={e2e_subprocess_timeout_sec!r}",
        file=sys.stderr,
        flush=True,
    )

    checks = run_http_suite_trace_stage(args, exec_stages, hb_sec=hb_sec)
    e2e, report_json_path = run_e2e_trace_stage_with_report_path(
        args,
        exec_stages,
        hb_sec=hb_sec,
        e2e_subprocess_timeout_sec=e2e_subprocess_timeout_sec,
    )
    return run_trace_review_artifact_phases_after_http_e2e(
        args,
        checks=checks,
        e2e=e2e,
        report_json_path=report_json_path,
        exec_stages=exec_stages,
        hb_sec=hb_sec,
        e2e_subprocess_timeout_sec=e2e_subprocess_timeout_sec,
    )


__all__ = ["run_agent_trace_review"]
