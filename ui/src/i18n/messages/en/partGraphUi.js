/** @type {Record<string, string>} */
export default {
  "graphShell.loading": "Loading graph…",

  "graph.workspacePanel.emptyHint":
    "Pick a paper or open the workspace graph (workspace_id query parameter).",

  "graph.wsToolbar.title": "Workspace graph",
  "graph.wsToolbar.modeInner": "Inner",
  "graph.wsToolbar.modeUnion1hop": "Union 1-hop",
  "graph.wsToolbar.modeSemantic": "Semantic",
  "graph.wsToolbar.modeFull": "Full",
  "graph.wsToolbar.depth1": "depth 1",
  "graph.wsToolbar.depth2": "depth 2",
  "graph.wsToolbar.external": "External",
  "graph.wsToolbar.statsWorks": "{{count}} works",
  "graph.wsToolbar.statsAuthors": "{{count}} authors",
  "graph.wsToolbar.statsExtCites": "{{count}} ext cites",
  "graph.wsToolbar.nodeType.Work": "Work",
  "graph.wsToolbar.nodeType.Author": "Author",
  "graph.wsToolbar.nodeType.Method": "Method",
  "graph.wsToolbar.nodeType.Dataset": "Dataset",
  "graph.wsToolbar.nodeType.Venue": "Venue",
  "graph.wsToolbar.nodeType.Institution": "Institution",

  "dedup.title": "Review duplicate papers (workspace scope)",
  "dedup.intro":
    "Clusters share the same DOI, arXiv id, OpenAlex id, or fingerprint. Choose which work to keep; merge re-points citations onto the kept work and syncs Qdrant payloads when the duplicate node is removed from Neo4j.",
  "dedup.loadingCandidates": "Loading candidates…",
  "dedup.noClusters": "No duplicate clusters in this workspace.",
  "dedup.candidateLine": "Candidate {{current}} / {{total}} · {{kind}} · key {{key}}",
  "dedup.loadingTitle": "Loading title…",
  "dedup.mergeActions": "Merge actions",
  "dedup.keep1merge2": "Keep 1, merge 2",
  "dedup.keep2merge1": "Keep 2, merge 1",
  "dedup.keep1merge3": "Keep 1 · merge 3",
  "dedup.skip": "Skip for now",
  "dedup.next": "Next",
  "dedup.prev": "Prev",
  "dedup.refresh": "Refresh list",
};
