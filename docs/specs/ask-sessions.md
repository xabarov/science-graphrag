# Ask sessions (Phase 5 MVP)

Local-only named **sessions** partition Ask history by **scope** so workspace and standalone flows do not mix lists.

## Scope keys

- **Standalone** (`/ask`, no workspace lock): `standalone`
- **Workspace Ask tab** (locked `work_id`): `workspace:{work_id}`

## Behavior

- Each scope has its own list of sessions (cap **8** per scope) and an **active** session id.
- Each session has a user-editable **title** (default `Session` + creation date) and an ordered list of **turns** (same fields as legacy history entries: query, work_id, top_k, answer snapshot, citations count, mode, savedAt).
- Cap **24** turns per session; oldest turns dropped when appending.
- **New session** creates an empty session and makes it active.
- **Rename** updates the title of the active session.
- **Switch session** via dropdown; **Recent** list shows the last **3** turns of the **active** session only.
- Legacy flat list in `science-graphrag:askHistory` is still updated by `rememberAskHistory` for backward compatibility and tests; first open of a scope may **import** legacy entries into one session titled `Imported` when no sessions exist yet.

## URL: `ask_session`

- Query parameter **`ask_session`** (see `TRACEABILITY_QUERY_KEYS.askSession` in [`traceabilityState.js`](../../ui/src/components/work/traceabilityState.js)) holds the **active session id** for deep links on **`/ask`** and **`/workspace?tab=ask`**.
- Changing the session in the UI updates the URL with **`replace: true`** (no history spam). Invalid or unknown ids are **removed** from the URL after load.
- Leaving the Ask workspace tab **clears** `ask_session` from the query string (see [`WorkspacePage.jsx`](../../ui/src/pages/WorkspacePage/WorkspacePage.jsx) `setTabParams`).
- Links built with **`mergeTraceabilityParams`** preserve `ask_session` when navigating between tabs (e.g. Graph → Ask) if it was already present.
- **Still local-only:** the id refers to `localStorage` on this browser; sharing the URL does not recreate sessions on another device.

## Out of scope (still)

- Server sync or multi-device sessions.
- Deleting sessions from UI or JSON export (future UX).
