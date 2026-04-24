/** @type {Record<string, string>} */
export default {
  "wsTab.overview.pickWork": "Select a work from Corpus to see an overview.",
  "wsTab.overview.loading": "Loading work…",
  "wsTab.overview.noTitle": "(no title)",
  "wsTab.overview.quickActions": "Quick actions",
  "wsTab.overview.readerTab": "Reader tab",
  "wsTab.overview.graphTab": "Graph tab",
  "wsTab.overview.askTab": "Ask tab",
  "wsTab.overview.evidenceTab": "Evidence tab",
  "wsTab.overview.openGraphFull": "Open graph (full page)",
  "wsTab.overview.graphNote":
    "Graph is now available inside workspace and still kept as a standalone route for deeper inspection.",
  "wsTab.overview.ingestionLine":
    "document_id: {{docId}} · has_chunks: {{hasChunks}} · semantic: {{semantic}}",

  "wsTab.reader.pickWork": "Pick a work from Corpus to load the reader.",
  "wsTab.reader.liveLine": "Live: GET /v1/works/{work_id} + /chunks.",
  "wsTab.reader.openStandalone": "Open standalone Reader",
  "wsTab.reader.jumpGraph": "Jump to Graph",
  "wsTab.reader.claimsTitle": "Claims (experimental)",
  "wsTab.reader.claimsLoading": "Loading claims…",
  "wsTab.reader.claimsEmpty": "No claims extracted for this work yet.",
  "wsTab.reader.claimConfidence": "confidence: {{v}}",

  "wsTab.graph.pickWork": "Pick a work from Corpus to inspect graph context.",
  "wsTab.graph.openStandalone": "Open standalone Graph",
  "wsTab.graph.jumpReader": "Jump to Reader",
  "wsTab.graph.jumpEvidence": "Jump to Evidence",
  "wsTab.graph.jumpAsk": "Jump to Ask",
  "wsTab.graph.subtitle":
    "Graph stays tied to the active work and keeps URL-driven node focus for deep links.",

  "wsTab.ask.pickWork": "Pick a work from Corpus to scope questions to that work.",
  "wsTab.ask.researchContext": "Research context",
  "wsTab.ask.contextLine": "Continue the current question flow from {{summary}}.",

  "wsTab.evidence.pickWork": "Pick a work from Corpus to inspect chunk fingerprints.",
  "wsTab.evidence.liveLine":
    "Live chunk fingerprints (GET /v1/works/{work_id}/chunks). Cross-check with Ask citations.",
  "wsTab.evidence.jumpReader": "Jump to Reader",
  "wsTab.evidence.jumpGraph": "Jump to Graph",
  "wsTab.evidence.openStandalone": "Open standalone Evidence",
};
