/** @type {Record<string, string>} */
export default {
  "glossary.workspace.p1": "Open a work and switch tabs without leaving context.",
  "glossary.workspace.p2": "is the indexed paper id; the",
  "glossary.workspace.p3": "ties Reader, Graph, Chat, and chunk inspection (/evidence) to that paper.",
  "glossary.workspace.session": "workspace session",

  "glossary.corpus.p1": "Browse indexed works",
  "glossary.corpus.p2":
    "Each row is a work_id in the corpus; open a work in Workspace for a full session (reader, chat, chunk inspection at /evidence, graph).",

  "glossary.ask.p1": "scopes the question to one indexed paper when you pick it from the corpus or paste an id. Leave empty for corpus-wide retrieval.",

  "glossary.graph.p1": "This graph is loaded for the active",
  "glossary.graph.p2": "Node selection syncs to the URL for deep links and traceability.",

  "home.header.eyebrow": "Research surface",
  "home.header.title": "Home",
  "home.header.description":
    "Open your workspace, browse Workspaces to add papers, or jump into admin tools without losing the main research flow.",
  "home.header.workspaces": "Workspaces",
  "home.header.admin": "Admin",

  "home.card.workspace.eyebrow": "Research surface",
  "home.card.workspace.titleOpenLast": "Open last paper workspace",
  "home.card.workspace.titleDefault": "Open Workspace",
  "home.card.workspace.descOpenLast":
    "Resume the most recently opened paper in the Workspace shell (paper list + tools in the left nav).",
  "home.card.workspace.descDefault": "Create or pick a workspace under Workspaces, then add papers by work id.",
  "home.card.workspace.openWorkspace": "Open Workspace",
  "home.card.workspace.lastPaper": "Last paper",
  "home.card.workspace.browse": "Browse Workspaces",

  "home.card.collections.eyebrow": "Collections",
  "home.card.collections.title": "Workspaces & indexed works",
  "home.card.collections.description":
    "Manage workspaces (paper sets), merge collections, export JSON, and search the indexed corpus to add papers.",
  "home.card.collections.workspaces": "Workspaces",
  "home.card.collections.reader": "Reader",

  "home.card.admin.eyebrow": "Operations surface",
  "home.card.admin.title": "Admin tools",
  "home.card.admin.description":
    "Benchmarks, settings, and diagnostics stay available from a dedicated entry, without dominating the core research journey.",
  "home.card.admin.openAdmin": "Open admin",
  "home.card.admin.benchmarks": "Benchmarks",

  "home.setup.eyebrow": "LLM setup",
  "home.setup.title": "Add your API key for full extraction",
  "home.setup.description":
    "The stack runs without it, but document extraction, PDF→Markdown (VL), and the research agent need an OpenAI-compatible key (e.g. OpenRouter). Configure it once in Settings — defaults match your server environment.",
  "home.setup.openSettings": "Open LLM settings",

  "home.recentWorks.title": "Recent works",
  "home.recentWorks.empty":
    "No recent works yet. Open Workspaces and add a paper to build a continue flow.",
  "home.recentWorks.open": "Open",

  "home.session.title": "Session readiness",
  "home.session.lastContext": "Last workspace context:",
  "home.session.recentHistory": "Recent work history:",
  "home.session.continueFlow": "Continue flow:",
  "home.session.savedLocally": "saved locally",
  "home.session.notSaved": "not saved yet",
  "home.session.available": "available",
  "home.session.empty": "empty",
  "home.session.readyResume": "ready to resume",
  "home.session.startsWorkspaces": "starts from Workspaces",

  "notFound.header.eyebrow": "Recovery",
  "notFound.header.title": "Page not found",
  "notFound.header.description":
    "This route does not exist or is no longer available. Choose a safe next step to return to the main research or admin flow.",
  "notFound.actions.title": "Recommended next actions",
  "notFound.actions.body":
    "Return to the main entry surfaces, reopen Workspaces, or continue the last saved workspace if you were in the middle of a research session.",
  "notFound.actions.goHome": "Go home",
  "notFound.actions.workspaces": "Workspaces",
  "notFound.actions.continueWorkspace": "Continue workspace",
  "notFound.actions.openAdmin": "Open admin",

  "adminGate.title": "Admin surface is unavailable",
  "adminGate.body":
    "This environment is currently running in research-only mode. Return to Workspaces or continue a workspace session without exposing operational tools.",
  "adminGate.goHome": "Go home",
  "adminGate.workspaces": "Workspaces",
  "adminGate.workspace": "Workspace",

  "adminEntry.apiStatus": "API status",
  "adminEntry.card.benchmarks.title": "Benchmarks",
  "adminEntry.card.benchmarks.description":
    "Run benchmark flows, inspect workbench output, compare runs, and review benchmark cases.",
  "adminEntry.card.benchmarks.primary": "Open benchmarks",
  "adminEntry.card.benchmarks.secondary": "Open workbench",
  "adminEntry.card.settings.title": "Settings",
  "adminEntry.card.settings.description":
    "Configure runtime and LLM settings with a dedicated settings layout that can grow over time.",
  "adminEntry.card.settings.primary": "Open settings",
  "adminEntry.card.diagnostics.title": "Diagnostics",
  "adminEntry.card.diagnostics.description":
    "Health and catalog probes plus JSON details. Extend with deeper metrics when backend exposes read-only status APIs.",
  "adminEntry.card.diagnostics.primary": "Open diagnostics",

  "adminApi.loading": "Loading API status…",
  "adminApi.health": "GET /health",
  "adminApi.works": "GET /v1/works",
  "adminApi.unreachable": "unreachable",
  "adminApi.catalogTotal": "catalog total {{total}}",
  "adminApi.reachable": "reachable",

  "diagnostics.title": "Diagnostics",
  "diagnostics.intro":
    "Run checks against the configured API base: GET /health and a minimal GET /v1/works?limit=1 probe. Deep runtime metrics remain a follow-up.",
  "diagnostics.apiBase": "API base:",
  "diagnostics.runChecks": "Run checks",
  "diagnostics.checking": "Checking…",
  "diagnostics.backAdmin": "Back to admin",
  "diagnostics.home": "Home",
  "diagnostics.success": "Checks completed. Inspect the JSON for health body and works catalog probe.",

  "reader.header.eyebrow": "Reader",
  "reader.header.title": "Article",
  "reader.header.descBefore": "Read extracted text for a",
  "reader.header.descAfter": ". Open from Workspace for the usual flow.",
  "reader.workIdLabel": "work_id",
  "reader.load": "Load",
  "reader.empty.title": "No work loaded",
  "reader.empty.body": "Enter a `work_id` above or start from Workspaces to open a paper.",
  "reader.openReaderWs": "Open Reader in workspace",
  "reader.openGraphWs": "Open Graph in workspace",

  "evidence.header.eyebrow": "Sources",
  "evidence.header.title": "Traceability",
  "evidence.header.description":
    "Chunk fingerprints and excerpt previews for auditing agent answers. Not a primary nav item: open from Chat citations, Reader trace, or paste a deep-link with work_id (optionally workspace_id).",
  "evidence.empty.title": "No evidence context loaded",
  "evidence.empty.body":
    "Open a paper from Workspaces / Workspace, then use Reader or a citation link. For support workflows, add ?dev=1 to reveal a work_id field.",
  "evidence.openLastWorkspace": "Open last workspace",
  "evidence.devAdvancedTitle": "Advanced: load by work_id",
  "evidence.devAdvancedHint": "Developer / support only. Prefer deep-links from Reader or Ask.",

  "askPage.header.eyebrow": "Chat",
  "askPage.header.title": "Chat",
  "askPage.header.description":
    "Agent chat scoped to one paper or the whole workspace. Pick a paper from the list or the context menu; you can also set work_id in the URL.",
  "askPage.empty.openLastWorkspace": "Open last workspace",

  "graph.toolbar.title": "Graph",
  "graph.toolbar.loadTooltip": "Load by work_id (advanced)",
  "graph.toolbar.loadAria": "Load graph by work id",
  "graph.toolbar.aboutTooltip": "About this page",
  "graph.toolbar.aboutAria": "Toggle page description",
  "graph.popover.hint":
    "Optional: paste a UUID to open a specific work. Prefer opening a paper from Workspace or Workspaces.",
  "graph.popover.cancel": "Cancel",
  "graph.popover.apply": "Apply",
  "graph.about.eyebrow": "Graph",
  "graph.about.title": "Inspection",
  "graph.about.description":
    "Use the left rail for Workspaces, Ask, and Evidence. Tips: ?lab=1 diagnostics, ?compact=1 denser UI, ?focus=1 hide side panels.",
  "graph.missing.title": "No graph context yet",
  "graph.missing.description":
    "Open a workspace graph (workspace_id) or a single paper (work_id) from Workspaces / Workspace, or use the key icon.",
  "graph.missing.footnote": "Tip: ?lab=1 expands diagnostics. ?compact=1 or ?focus=1 tighten layout.",
  "graph.openLastWorkspace": "Open last workspace",

  "settings.snapshot.general.label": "General",
  "settings.snapshot.general.description": "Environment, app identity, and global defaults.",
  "settings.snapshot.llm.label": "LLM",
  "settings.snapshot.llm.description": "Provider endpoint, model defaults, credentials, and test tools.",
  "settings.snapshot.ingestion.label": "Ingestion",
  "settings.snapshot.ingestion.description": "PDF, front-matter, references, and extraction pipeline tuning.",
  "settings.snapshot.storage.label": "Storage & Integrations",
  "settings.snapshot.storage.description":
    "Neo4j, Qdrant, Postgres, Redis, mandatory MinIO/S3, and local mirror paths for blobs/artifacts.",
  "settings.snapshot.benchmark.label": "Benchmark",
  "settings.snapshot.benchmark.description": "Teacher/student defaults and benchmark-specific execution knobs.",
  "settings.snapshot.security.label": "Security & Access",
  "settings.snapshot.security.description": "Permissions, access model, and secret governance.",
  "settings.snapshot.diagnostics.label": "Diagnostics",
  "settings.snapshot.diagnostics.description": "Connection status, recent tests, and runtime environment diagnostics.",
};
