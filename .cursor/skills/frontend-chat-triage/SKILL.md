---
name: frontend-chat-triage
description: Триаж «чат не работает» / SSE агента — отделить backend, nginx, HMR, abort.
---

# Frontend chat triage (Ask / agent SSE)

Используй при сообщениях вроде: «чат не работает», «нет ответа в чате», «agent stream stuck», «final_answer not received», «чат сбрасывается».

Рабочая директория для команд — корень репозитория `science-graphrag`, compose-файл dev: `docker-compose.dev.yml`.

## 1. Backend отдаёт поток?

Отделить API от UI. Пример (подставь валидный `workspace_id` и при необходимости заголовок авторизации):

```bash
curl -sS -N -X POST "http://localhost/v2/agent/query" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"question":"ping","workspace_id":"<uuid>","max_tool_calls":2}' | tail -5
```

Ожидание: в конце потока есть событие с `final_answer` (или явная ошибка в JSON внутри SSE). Если здесь пусто или обрыв — смотреть `docker compose -f docker-compose.dev.yml logs api`.

## 2. Nginx и буферизация

```bash
docker compose -f docker-compose.dev.yml logs web --tail=200 | rg "v2/agent"
```

Убедиться, что для dev-конфига у `location ^~ /v2/agent/` включён `proxy_buffering off` (см. `docker/nginx-web.dev.conf`). Иначе SSE может «залипать» или обрываться на прокси.

## 3. Vite HMR — full reload?

```bash
docker compose -f docker-compose.dev.yml logs ui --tail=400 | rg -i "could not fast refresh|page reload"
```

`Could not Fast Refresh` или лавина `page reload` на модулях из графа чата — типичная причина «отправил вопрос — через пару секунд пусто»: полный reload отменяет `fetch` к `/v2/agent/query`. См. правило `.cursor/rules/frontend-hmr-and-fast-refresh.mdc` и разнесение `I18nProvider` / `useI18n`, `WorkspaceContextProvider` / `useWorkspaceContext`.

## 4. Браузер: Network

DevTools → Network → запрос `POST .../v2/agent/query`:

- Статус `(canceled)` или очень короткое время при ожидаемом длинном ответе — навигация, unmount, новый submit, или full reload (п. 3).
- `200` и растущий ответ, но UI пустой — смотреть парсер SSE (`useAgentStream`, `agentStreamParse.js`) и отрисовку (`useAskSubmit`, `ChatMessageThread`).

## 5. Сообщения об ошибке в UI

В [`ui/src/hooks/useAgentStream.js`](../../../ui/src/hooks/useAgentStream.js) при завершении стрима без `final_answer` вызывается `onError` с текстом вроде «Stream ended before a final answer was received.» — это отличает **обрыв/abort** от успешного пустого ответа.

## Итог

Сначала 1 → 2 → 3 → 4 → 5. Не начинать с правок агента в Python, пока curl (п. 1) и HMR-логи (п. 3) не прояснены.
