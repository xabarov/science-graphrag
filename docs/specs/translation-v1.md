# Translation API v1 (LX2)

## Status

Draft — 2026-04-26 / updated 2026-04-27: SSE stub endpoints mounted; Postgres schema applied via Alembic `20260426_0007_work_translations` (ORM `WorkTranslationRecord`). LLM translation, cache reads/writes from handlers, and Phoenix spans — **not** implemented yet.

## Endpoints

- `POST /v1/works/{work_id}/translate/abstract` — `text/event-stream` SSE; events: `queued`, `done` (stub).
- `POST /v1/works/{work_id}/translate/body` — same contract (stub).

## Persistence

Postgres table **`work_translations`** (Alembic revision `20260426_0007`): columns `work_id`, `locale`, `field` (`abstract` \| `body`), `text`, `model`, `created_at`; unique key `(work_id, locale, field)` (`uq_work_translation_key`). Endpoints do not read/write this table yet.

## Cost guardrails

- Document expected OpenRouter cost per ~10k-token article before enabling production translation.
- Client must support **Cancel** (abort fetch) on SSE streams.
