/** @type {Record<string, string>} */
export default {
  "askPanel.chromeTitle": "Ask",
  "askPanel.chromeBody":
    "POST /v1/query (live). Set VITE_API_BASE_URL if the API is not same-origin.",
  "askPanel.chrome.p1": "POST /v1/query (live). Set ",
  "askPanel.chrome.p2": " if the API is not same-origin.",
  "askPanel.banner.workspaceScoped": "Workspace-scoped research",
  "askPanel.banner.standalone": "Standalone research",
  "askPanel.banner.descWorkspace":
    "Question is scoped to the active work. Use citations below to jump into evidence, reader context, and graph context without losing `work_id`.",
  "askPanel.banner.descStandalone":
    "Ask across the corpus or pick one paper first. Use the answer actions below to move into evidence, reader context, or graph context when you need deeper inspection.",
  "askPanel.banner.workspaceCorpusTitle": "Workspace corpus scope",
  "askPanel.banner.descWorkspaceCorpus":
    "Questions are limited to papers in the active workspace (no single work_id). Add an optional work_id below to narrow further.",
  "askPanel.optionalContext.title": "Optional work context",
  "askPanel.session.title": "Ask session",
  "askPanel.session.hintStandalone":
    "Stored locally in this browser. Each session keeps its own turn list (up to 24 turns).",
  "askPanel.session.hintWorkspace": "Stored per work for this workspace tab. Switch sessions to separate threads.",
  "askPanel.session.serverSyncLine":
    "Server sync writes to /v1/ask-sessions (file-backed on the API host).",
  "askPanel.session.urlLine":
    "The active session id is reflected in the URL as ask_session (local browser only; safe to share only on trusted channels).",
  "askPanel.serverSyncLabel": "Server session sync (pilot)",
  "askPanel.session.selectLabel": "Session",
  "askPanel.sessionTitle": "Session title",
  "askPanel.newSession": "New session",
  "askPanel.recent.standalone": "Recent in this session",
  "askPanel.recent.workspace": "Recent in this workspace session",
  "askPanel.recent.globalLine": "global corpus · ",
  "askPanel.recent.topK": "top_k {{k}} · {{count}} citations",
  "askPanel.restore": "Restore",
  "askPanel.noTurns.title": "No turns yet",
  "askPanel.noTurns.body":
    "Run a query to populate this session. Enable server sync if you want the API host to persist turns for the same scope.",
  "askPanel.workIdScopeLabel": "work_id (workspace scope)",
  "askPanel.query": "Query",
  "askPanel.workIdAutocomplete": "work_id (optional, pick from corpus)",
  "askPanel.topK": "top_k",
  "askPanel.retrieval.modeLabel": "Retrieval mode (lab / admin)",
  "askPanel.retrieval.vector": "vector",
  "askPanel.retrieval.hybrid": "hybrid",
  "askPanel.runQueryLoading": "Querying…",
  "askPanel.runQuery": "Run query",
  "askPanel.openStandaloneAsk": "Open standalone Ask",
  "askPanel.answer.title": "Answer",
  "askPanel.answer.why": "Why this answer",
  "askPanel.answer.degraded":
    "Some context had to degrade during retrieval. Review the trace details below before using this answer as a final conclusion.",
  "askPanel.citations.title": "Citations",
  "askPanel.citations.none": "No supporting citations were returned for this answer.",
  "askPanel.citation.line": "Citation #{{rank}} · score {{score}} · {{work}}",
  "askPanel.citation.noWork": "no work context",
  "askPanel.chunkLabel": "chunk",
  "askPanel.openReader": "Open Reader",
  "askPanel.openEvidence": "Open Evidence",
  "askPanel.openGraph": "Open Graph",
  "askPanel.openInWorkspace": "Open in Workspace",
  "askPanel.standaloneReader": "Standalone Reader",
  "askPanel.standaloneEvidence": "Standalone Evidence",
  "askPanel.standaloneGraph": "Standalone Graph",
  "askPanel.graphContext.title": "Graph context",
  "askPanel.graphContext.body":
    "semantic_available={{semantic}} · context_work_id={{ctx}}{{err}}",
  "askPanel.retrieval.title": "Retrieval trace",
  "askPanel.retrieval.summary":
    "Summary of how evidence was retrieved. Expand advanced for the full JSON (embedding and low-level fields).",
  "askPanel.toggleJson.hide": "Hide advanced JSON",
  "askPanel.toggleJson.show": "Show advanced JSON",
  "askPanel.flag.graphDegraded": "graph_context.degraded",
};
