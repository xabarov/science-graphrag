# Phoenix Wave X closeout — live evidence (2026-04-27)

Краткий снимок **фактов с локального Phoenix** (`PHOENIX_UI_BASE_URL=http://127.0.0.1:16006`, project `science-graphrag`) и **артефактов roadmap harness** после follow-up по project-aware REST и OTel propagation.

## 1) Ingest — LLM models, токены, VL

**Phoenix REST** (примеры `GET /v1/projects/science-graphrag/spans?name=…`):

| Span name | Пример `trace_id` | `llm.model_name` | `llm.token_count.total` (пример) |
|-----------|-------------------|------------------|----------------------------------|
| `llm.metadata_extraction` | `67d1350913f6c30db0c361dfd9d11c0d` | `mistralai/mistral-small-3.2-24b-instruct` | 10298 / 3250 (два вызова в trace) |
| `llm.authorships_extraction` | то же | то же | 10038 |
| `llm.references_extraction` | то же | то же | 68591 |
| `llm.vl_pdf` | `3a4c220453e90daf1c473f24c9230248` | `qwen/qwen3-vl-235b-a22b-instruct` | 34 |

Интерпретация: в Phoenix → **Settings → Models** для обеих кастомных моделей есть **ненулевые** LLM-спаны с токенами на реальных ingest-трейсах (конкретные числа зависят от документа и провайдера).

**Sessions (`session.id = job_id`):** корреляция задана в пайплайне ingest (см. X1.6 в основном документе и `ingest_jobs.phoenix_trace_id`). На старых трейсах в локальном Phoenix поле `session.id` у корня может отсутствовать; для строгой UI-проверки используйте свежий ingest через API/CLI после деплоя X1.6.

## 2) Agent — один trace, TOOL + RETRIEVER, live audit

| Кейс | Артефакты | `phoenix_trace_id` | Observability |
|------|-----------|--------------------|---------------|
| `inventory_papers` | `eval/results/chat-agent-live-verify-20260427-093918/cases/inventory_papers/trace_audit.json` | `3382397beb368acf5e77735b37660af2` | `observability_match_reliable=true`, `phoenix_payload_kind=span_list`, `missing_tool_spans=[]` |
| `quote_detection` (RETRIEVER) | `eval/results/chat-agent-closeout-retriever-20260427-095104/cases/quote_detection/trace_audit.json` | `646fec014d00716dac8fe6e5d20200d8` | ожидался `retrieval.qdrant.paper_quote_search` — **в списке `expected_span_names`, `missing_retriever_spans=[]`** |

Deep link (Phoenix 13.x UI): `http://127.0.0.1:16006/projects/science-graphrag/traces/<phoenix_trace_id>` (см. `phoenix_ui_hint` в каждом `trace_audit.json`).

## 3) `PHOENIX_TRACE_SCOPE=extraction_llm`

Код: [`science_graphrag/observability/scope.py`](../../science_graphrag/observability/scope.py) — allowlist дополнен `llm.vl_pdf`, `llm.claims_extraction`, CHAIN `ingest.extract_claims.llm`.

Тест: [`tests/observability/test_extraction_llm_scope.py`](../../tests/observability/test_extraction_llm_scope.py).

## 4) Команды для воспроизведения

```bash
# Agent + fetch Phoenix (один кейс)
PHOENIX_UI_BASE_URL=http://127.0.0.1:16006 PHOENIX_TRACE_SCOPE=full \
  .venv/bin/science-graphrag-chat-agent-roadmap \
  --fixtures tests/fixtures/benchmarks/chat_agent_roadmap \
  --out eval/results/chat-agent-closeout-retriever-latest \
  --case 04_quote_detection --fetch-phoenix
```

```bash
# Проверка ingest LLM в Phoenix REST
curl -sS "http://127.0.0.1:16006/v1/projects/science-graphrag/spans?name=llm.vl_pdf&limit=3" | jq '.data[0].context.trace_id, .data[0].attributes["llm.model_name"]'
```
