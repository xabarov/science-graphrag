#!/usr/bin/env bash
# Bundle: prompt bundle gate + OD workspace full E2E with trace audit and Markdown report.
# Usage: from repo root: scripts/live_check/run_agent_od_phases_audit.sh [markdown_out_path]
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"
PY="${REPO_ROOT}/.venv/bin/python"
if [[ ! -x "${PY}" ]]; then
  echo "Expected venv at ${PY}" >&2
  exit 1
fi
"${PY}" scripts/prompt_audit/build_research_chat_prompt_bundle.py --evaluate
OUT="${1:-${REPO_ROOT}/eval/results/agent-od-phases-audit-$(date -u +%Y%m%dT%H%M%SZ).md}"
mkdir -p "$(dirname "${OUT}")"
"${PY}" scripts/live_check/agent_od_workspace_e2e_audit.py \
  --suite full \
  --trace-audit \
  --markdown-report "${OUT}"
echo "Markdown report: ${OUT}"
