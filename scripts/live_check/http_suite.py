"""Reusable HTTP checks for a running science-graphrag API (agent v2).

Used by ``scripts/live_check/agent_v2_http.py`` and optional pytest under ``tests/live/``.

Implementation is split into ``http_suite_core`` (health + envelope) and
``http_suite_agent_v2`` (agent v2 checks + default suite); this module re-exports
the historical import surface when ``scripts/live_check`` is on ``sys.path``.

Operator notes (env vars, CH4 gate): see ``scripts/live_check/README.md``.
"""

from __future__ import annotations

from http_suite_agent_v2 import (
    check_agent_v2_fanout_probe,
    check_agent_v2_malicious_deny,
    check_agent_v2_sse,
    check_agent_v2_sync_json,
    check_multi_turn_digest,
    run_default_suite,
)
from http_suite_core import (
    CheckResult,
    _ANSWER_STRIP_MAX_FOR_CHECK_PAYLOAD,
    _extra_headers,
    check_health,
)

__all__ = [
    "CheckResult",
    "_ANSWER_STRIP_MAX_FOR_CHECK_PAYLOAD",
    "_extra_headers",
    "check_agent_v2_fanout_probe",
    "check_agent_v2_malicious_deny",
    "check_agent_v2_sse",
    "check_agent_v2_sync_json",
    "check_health",
    "check_multi_turn_digest",
    "run_default_suite",
]
