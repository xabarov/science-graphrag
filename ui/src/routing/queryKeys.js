/**
 * Canonical HTTP query parameter names shared by `/workspace`, standalone tools, and traceability deep links.
 * Keep in sync with server expectations and bookmark URLs.
 */

/** Keys used by the workspace shell URL (`/workspace?...`) and all tool deep links. */
export const WORKSPACE_SHELL_QUERY_KEYS = {
  workId: "work_id",
  workspaceId: "workspace_id",
};

/**
 * Full traceability / session query schema (workspace + standalone routes).
 * @see ../../components/work/traceabilityState.js for read/build/merge helpers.
 */
export const TRACEABILITY_QUERY_KEYS = {
  ...WORKSPACE_SHELL_QUERY_KEYS,
  tab: "tab",
  nodeId: "node",
  /** Normalized graph edge id (Canvas selection); mutual exclusion with `nodeId` for deep links. */
  edgeId: "edge",
  chunkFingerprint: "chunk_fingerprint",
  section: "section",
  citation: "citation",
  /** Local Ask session id (browser-only; preserved across workspace links when present). */
  askSession: "ask_session",
};
