# Ask Module Map

This directory contains the Ask/chat feature split by domain.

## Public API (stable imports)

External consumers (`pages/`, `traceability/`, etc.) should import from:

- `ui/src/components/work/ask/index.js`

Current public exports:

- `AskPanel`
- `sessionExistsInScope`
- `deriveAskScopeKey`

Avoid deep imports into subfolders from outside `ask/`.

## Internal layout

- `shell/`
  - Top-level composition shell (`AskPanel`, `AskPanelChrome`)
- `orchestration/`
  - Ask panel orchestrator hooks and contract checks
- `session/`
  - Session state/model/storage/server bridge and related helpers
- `chat/`
  - Chat thread/composer UI pieces, chat preferences, scroll logic
- `answer/`
  - Answer panel, source list, citation formatting/hydration helpers
- `forms/`
  - Structured Ask forms (research plan and user question form)

## Change rules

- Keep cross-domain dependencies directional:
  - `shell` -> `orchestration` -> (`session`, `chat`, `answer`, `forms`)
- Prefer moving shared pure helpers into the nearest domain folder first.
- If a symbol is needed by external modules, re-export it from `index.js`.
