# Prompt audit (research chat)

Assembles the **system prompt + LangChain tool descriptions + JSON Schemas** seen next to
`bind_tools` (mock stores). See [`docs/architecture/agent-tools-best-practices.md`](../../docs/architecture/agent-tools-best-practices.md).

## Commands

From repository root:

```bash
.venv/bin/python scripts/prompt_audit/build_research_chat_prompt_bundle.py --evaluate
.venv/bin/python scripts/prompt_audit/build_research_chat_prompt_bundle.py --evaluate --json
# Gates + markdown artifact (metrics appendix included):
.venv/bin/python scripts/prompt_audit/build_research_chat_prompt_bundle.py --evaluate \\
  -o scripts/prompt_audit/_artifacts/research_chat_prompt_bundle.md
```

CI entrypoint (same gates as `--evaluate`):

```bash
.venv/bin/python scripts/prompt_audit/evaluate_research_chat_prompt_bundle.py
```

Generated markdown under `_artifacts/` is gitignored; regenerate before release reviews.
