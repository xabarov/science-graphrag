/**
 * Standalone `/graph` URL helpers: layout flags and preserving chrome params when editing `work_id`.
 *
 * ## Query contract (GraphPage)
 *
 * **Shared traceability / work context** (see `TRACEABILITY_QUERY_KEYS` in `./queryKeys.js` and
 * `readTraceabilityState` in `components/work/traceabilityState.js`): `work_id`, `workspace_id`,
 * `node`, `edge`, plus optional reader/evidence fields when deep-linking across tools.
 *
 * **Graph-page local chrome** (this module only — do not merge via `mergeTraceabilityParams` unless
 * product explicitly wants selection + lab flags in one atomic update): `lab`, `compact`, `focus`
 * drive denser UI / experimental toggles. `GraphPage.applyWorkId` rebuilds params and copies these
 * keys via {@link preserveGraphPageOptionalParams}.
 */

import { WORKSPACE_SHELL_QUERY_KEYS } from "./queryKeys.js";

/** Query keys specific to GraphPage layout / lab mode (not part of traceability merge). */
export const GRAPH_PAGE_QUERY_KEYS = {
  lab: "lab",
  compact: "compact",
  focus: "focus",
};

/** @param {URLSearchParams} searchParams */
export function readGraphPageLayoutFlags(searchParams) {
  const compact = searchParams.get(GRAPH_PAGE_QUERY_KEYS.compact) === "1";
  const focus = searchParams.get(GRAPH_PAGE_QUERY_KEYS.focus) === "1";
  return {
    compact,
    focus,
    /** Denser graph panel defaults; `focus` implies this as well. */
    compactLayout: compact || focus,
  };
}

/**
 * Copy optional graph layout/lab flags from the previous query into `params`.
 * @param {URLSearchParams} params
 * @param {URLSearchParams} prev
 */
export function preserveGraphPageOptionalParams(params, prev) {
  if (prev.get(GRAPH_PAGE_QUERY_KEYS.lab) === "1") params.set(GRAPH_PAGE_QUERY_KEYS.lab, "1");
  if (prev.get(GRAPH_PAGE_QUERY_KEYS.compact) === "1") params.set(GRAPH_PAGE_QUERY_KEYS.compact, "1");
  if (prev.get(GRAPH_PAGE_QUERY_KEYS.focus) === "1") params.set(GRAPH_PAGE_QUERY_KEYS.focus, "1");
  const ws = prev.get(WORKSPACE_SHELL_QUERY_KEYS.workspaceId);
  if (ws && String(ws).trim()) {
    params.set(WORKSPACE_SHELL_QUERY_KEYS.workspaceId, String(ws).trim());
  }
}
