# UI empty, loading, and error states — audit checklist (Phase 7)

Cross-cutting quality pass for `ui/src/pages/**` and heavy components (`GraphWorkspacePanel`, `AskPanel`, `ReaderWorkBody`, `CorpusPage`, `BenchmarkPage`).

## Principles

- **One vocabulary** — reuse `graphShellStates` patterns where possible; same typography and spacing for empty vs error.
- **Actionable next step** — every empty state suggests ingest, pick `work_id`, or check API base URL.
- **No silent failure** — network errors show `formatResearchApiError` output; degraded flags from API surfaced as `Alert` with severity `warning` vs `error`.

## Page checklist

| Surface | Loading | Empty | Error |
|---------|---------|-------|-------|
| Corpus | Circular + copy | “No works” card | Red `Alert` |
| Workspace tabs | Tab skeleton or spinner | Work-specific hints | `Alert` + retry |
| Graph | `GraphShellStates` | No neighborhood | Neo4j / API errors |
| Ask | Query button disabled state | No history yet | LLM / API errors |
| Evidence | Chunk list skeleton | No citations | Missing work |
| Benchmarks | Run progress | No cases / runs | 413 / run store errors |
| Admin / Diagnostics | Strip pending | Partial probes | HTTP failures |

## Exit

- All rows above reviewed on desktop viewport; mobile breakpoints noted if broken.
- Follow-ups filed in [ui-ux-master-plan](./ui-ux-master-plan.md) Phase 7 or graph-ui-plan if graph-specific.

**Progress (2026-04-19):** Ask — добавлен явный empty-state для пустой истории сессии; Benchmark/Settings — заголовок `X-Admin-Key` через [`ui/src/services/adminApiHeaders.js`](../../ui/src/services/adminApiHeaders.js) (см. `VITE_ADMIN_API_KEY` / `ui/.env.local`). Остальные строки таблицы — по-прежнему живой чеклист для десктоп-ревью.
