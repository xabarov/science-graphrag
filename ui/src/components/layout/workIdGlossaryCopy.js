/** Canonical UI copy for work_id (English product strings). */

export const WORK_ID_QUERY_PARAM = "work_id";

export const WORK_ID_GLOSSARY_COPY = {
  /** Corpus browser header (before API chip) */
  corpusIntroPrefix: "Browse indexed works",
  /** Corpus browser header (after API chip) */
  corpusIntroRest:
    "Each row is a work_id in the corpus; open a work in Workspace for a full session (reader, ask, evidence, graph).",
  /** Optional paper scope on standalone Ask (after leading work_id label) */
  askOptionalWorkRest:
    "scopes the question to one indexed paper when you pick it from the corpus or paste an id. Leave empty for corpus-wide retrieval.",
  /** Graph tab / panel — body after leading phrase */
  graphScopedRest: "Node selection syncs to the URL for deep links and traceability.",
};
