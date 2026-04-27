# Chat agent roadmap regression fixtures

Canonical **benchmark-backed workspace** for chat-agent use-case runs (see
[`baseline_workspace_manifest.json`](./baseline_workspace_manifest.json)).

This workspace id matches retrieval and agent-tools benchmarks (`ws-pilot-od`).

If Neo4j returns `workspace_not_found` during audit, run once (idempotent):

```bash
.venv/bin/python scripts/seed_benchmark_workspaces.py
```

## Layout

- `baseline_workspace_manifest.json` — stable id, description, links to related benchmark gold.
- `cases/*.json` — curated use cases (see slim roadmap + trace-audit doc; historical mapping to full roadmap §2 in `docs/analysis/_archive/chat-agent-system-roadmap-full-2026-04-26.md`).

## Runner

From repo root (requires live stores + LLM keys like other agent benchmarks):

```bash
.venv/bin/science-graphrag-chat-agent-roadmap \
  --fixtures tests/fixtures/benchmarks/chat_agent_roadmap \
  --out eval/results/chat-agent-roadmap-latest
```

Pre-flight data audit only:

```bash
.venv/bin/python scripts/chat_agent_workspace_readiness_audit.py \
  --manifest tests/fixtures/benchmarks/chat_agent_roadmap/baseline_workspace_manifest.json \
  --out-json eval/results/chat-agent-roadmap-workspace-audit.json
```
