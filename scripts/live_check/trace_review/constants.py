"""Version and gate thresholds for trace-review-v1."""

from __future__ import annotations

REVIEW_VERSION = "trace-review-v1"
TOOL_LOOP_REPEAT_FAIL_THRESHOLD = 3
WRITER_OSCILLATION_ACCEPTANCE_MAX = 1
DEFAULT_ACCEPTABLE_WARN_PATTERNS = (r"^claim_verification_verdict_parse_rate:absent_no_cv_rows$",)
VERDICT_OK_STATES = frozenset({"PASS", "FAIL", "PARTIAL"})
WRITER_SPECIALIST_ID = "writer_agent"
