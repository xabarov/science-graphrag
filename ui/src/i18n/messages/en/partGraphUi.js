/** @type {Record<string, string>} */
export default {
  "graphShell.loading": "Loading graph…",
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
