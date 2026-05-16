# Ollama OpenAI-compatible smoke (local)

Use this runbook after saving LLM settings with the **Ollama local** preset (or equivalent manual values).

## Prerequisites

- Ollama daemon running (`ollama serve` or desktop app).
- Models pulled before first request (cold start is slow).
- If API runs in Docker, container-to-host access must be configured (see `docker-compose.dev.yml` `extra_hosts` for `host.docker.internal:host-gateway`).

```bash
ollama --version
ollama list
curl -s http://localhost:11434/v1/models | head
```

## Recommended settings (UI preset)

| Task | Base URL | Model (example) | API key | Timeout (s) |
|------|----------|-------------------|---------|-------------|
| Extraction | `http://localhost:11434/v1` | `llama3.2` | `ollama` | 300 |
| Chat | same | `llama3.2` | `ollama` | 300 |
| Vision | same | `llava` (if used) | `ollama` | 300 |
| Embeddings | same | `all-minilm` | `ollama` | 120 |

Ollama **ignores** the API key; OpenAI-compatible clients still require a non-empty value.

## Pull models

```bash
ollama pull llama3.2
ollama pull all-minilm
# optional vision
ollama pull llava
```

## Raw HTTP smoke

### Chat completions

```bash
curl -s http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ollama" \
  -d '{
    "model": "llama3.2",
    "messages": [{"role": "user", "content": "Reply with exactly OK."}],
    "stream": false,
    "max_tokens": 12
  }'
```

### Embeddings

```bash
curl -s http://localhost:11434/v1/embeddings \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ollama" \
  -d '{
    "model": "all-minilm",
    "input": ["hello", "world"]
  }'
```

## App-level smoke

From repo root with venv and API up:

1. Save LLM settings (UI or `PATCH /v1/settings/llm` with `tasks` + `api_key: ollama`).
2. `GET /v1/settings` → `llm.diagnostics.probable_ollama_endpoint` should be `true`.
3. Settings → **Test saved configuration** (extraction probe).
4. Optional: one short agent turn without relying on `tool_choice` or streaming tools.

## Linux + Docker practical setup

When Ollama binds only to `127.0.0.1:11434`, host raw checks pass but API container cannot reach it.

Recommended stable options:

1. Keep Ollama local loopback for host checks (`http://127.0.0.1:11434/v1`).
2. For container-facing LLM settings, use host gateway URL:
   - `http://host.docker.internal:11434/v1` (with `extra_hosts` in compose).
   - or explicit bridge gateway IP (e.g., `http://172.19.0.1:11434/v1`) if needed.

### One-command live smoke (this repo)

```bash
AGENT_LIVE_BASE=http://127.0.0.1:18787 \
.venv/bin/python scripts/live_check/ollama_local_smoke.py \
  --ollama-base-url http://127.0.0.1:11434/v1 \
  --settings-ollama-base-url http://host.docker.internal:11434/v1 \
  --chat-model gemma4 \
  --embeddings-model qwen3-embedding:0.6b \
  --timeout 180
```

If your host alias is unavailable, replace `host.docker.internal` with your Docker bridge gateway IP.

## Known limitations

- Ollama OpenAI compatibility is **experimental** (upstream may break).
- Structured extraction / instructor JSON may vary by model.
- Agent tool calling: test per model; `tool_choice` not supported on OpenAI-compatible layer.
- Vision depends on a vision-capable local model and image input format.

## Unit tests (no daemon)

```bash
.venv/bin/pytest tests/test_llm_provider_compat.py tests/test_runtime_overlay.py::test_build_non_secret_overrides_ollama_embeddings_task -q
cd ui && npm test -- --run src/pages/SettingsPage/llmProviderPresets.test.js src/pages/SettingsPage/LlmSettingsPanel.test.jsx
```
