/** @type {Record<string, string>} */
export default {
  "workspace.paper.loading": "Loading paper…",
  "workspace.paper.noTitle": "(no title)",
  "workspace.paper.hint":
    "Open Reader for extracted text. Use workspace actions in the header for graph, ask, and summaries across all papers.",
  "workspace.paper.hintSuffix": "Click the card (outside links) to focus this paper in the URL.",
  "workspace.paper.reader": "Reader",
  "workspace.paper.workGraph": "Paper graph",
  "workspace.actions.askWorkspace": "Ask (workspace)",
  "workspace.paper.yearChip": "Year {{year}}",
  "workspace.paper.doiChip": "DOI {{doi}}",

  "workspace.err.notFound": "Workspace not found.",
  "workspace.empty.alert":
    "No workspace yet. Create one under Workspaces, then upload a PDF / text or attach an existing indexed work_id.",
  "workspace.empty.workspaces": "Workspaces",
  "workspace.empty.about": "About",

  "workspace.header.eyebrow": "Workspace",
  "workspace.header.titleFallback": "Papers",
  "workspace.header.loadingWs": "Loading workspace…",
  "workspace.header.paperCountOne": "{{count}} paper in this workspace.",
  "workspace.header.paperCountMany": "{{count}} papers in this workspace.",
  "workspace.header.focusedPaper": "Focused paper:",
  "workspace.header.workspaceGraph": "Workspace graph",
  "workspace.header.summarizing": "Summarizing...",
  "workspace.header.summarizeAction": "Summarize this workspace",
  "workspace.header.generatingHypotheses": "Generating...",
  "workspace.header.generateHypotheses": "Generate hypotheses",
  "workspace.header.graphStatsLine":
    "Graph: {{works}} works · {{authors}} authors · {{internal}} internal cites · {{external}} external cites",
  "workspace.summary.dialogTitle": "Workspace summary",
  "workspace.summary.empty": "No summary yet.",
  "workspace.idea.dialogTitle": "Hypothesis / contradiction assist",
  "workspace.dialog.close": "Close",

  "workspace.upload.title": "Upload article",
  "workspace.upload.desc":
    "PDF, Markdown, or plain text. Processing runs on the server; this page polls until done, then refreshes the paper list.",
  "workspace.upload.starting": "Starting…",
  "workspace.upload.processing": "Processing…",
  "workspace.upload.chooseFile": "Choose file",
  "workspace.upload.chooseMultiple": "Multiple files",
  "workspace.upload.chooseZip": "Upload .zip",
  "workspace.upload.dropHint": "Or drag and drop files or a folder here (PDF / Markdown / text).",
  "workspace.upload.jobLine": "job {{id}} · {{status}}",
  "workspace.upload.newWorkId": "New work_id:",
  "workspace.upload.dash": "—",
  "workspace.ingest.progressLabel": "Overall progress: {{pct}}%",
  "workspace.ingest.detailsLogs": "Details / logs",

  "workspace.advanced.accordion": "Advanced: add existing work_id",
  "workspace.advanced.workIdLabel": "work_id",
  "workspace.advanced.placeholder": "Existing indexed work id",
  "workspace.advanced.add": "Add to workspace",

  "workspace.noPapers":
    "No papers yet. Upload a file above, or add an existing work_id from the catalog under Workspaces.",

  "workspace.side.graphTitle": "Graph snapshot",
  "workspace.side.graphStatsLine":
    "{{works}} works · {{authors}} authors · {{internal}} internal cites · {{external}} external cites",
  "workspace.side.dedupTitle": "Smart dedup",
  "workspace.side.dedupPendingLine": "Pending near-duplicate reviews: {{count}}",
  "workspace.side.dedupPendingUnknown": "Run a scan in the section below to refresh the queue.",
  "workspace.side.dedupJump": "Open dedup section",
};
