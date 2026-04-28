/**
 * @fileoverview Central routing and deep-link contract for the UI under `HashRouter`.
 *
 * ## Pathname (navigation scope)
 *
 * Primary surfaces use constants from `../routes/paths.js`: {@link WORKSPACE_PATH}, {@link READER_PATH},
 * {@link GRAPH_PATH}, {@link CHAT_PATH}, {@link EVIDENCE_PATH}. The shell drawer navigates by
 * pathname inside the hash (e.g. `#/graph`).
 *
 * ## Query string (work context + traceability)
 *
 * {@link TRACEABILITY_QUERY_KEYS} defines shared query names (`work_id`, `workspace_id`, `node`,
 * `edge`, chunk/section/citation, legacy `tab`, etc.). Read/merge/build helpers live in
 * `components/work/traceabilityState.js` and are re-exported below for a single import path.
 *
 * **`includeTab: false`:** Standalone tool URLs must not add legacy workspace `tab=` when merging
 * params (e.g. graph selection updates on `/graph`).
 *
 * ## Graph page local chrome
 *
 * {@link GRAPH_PAGE_QUERY_KEYS} (`lab`, `compact`, `focus`) are not part of traceability merges;
 * use {@link readGraphPageLayoutFlags} / {@link preserveGraphPageOptionalParams} from `./graphPageQuery.js`.
 *
 * ## Legacy workspace tabs
 *
 * Old `/workspace?tab=reader|graph|ask` bookmarks are redirected via {@link legacyWorkspaceTabRedirectTarget}
 * (see `useWorkspacePageCore.jsx`).
 */

export { WORKSPACE_SHELL_QUERY_KEYS, TRACEABILITY_QUERY_KEYS } from "./queryKeys.js";
export {
  GRAPH_PAGE_QUERY_KEYS,
  preserveGraphPageOptionalParams,
  readGraphPageLayoutFlags,
} from "./graphPageQuery.js";
export {
  CHAT_PATH,
  EVIDENCE_PATH,
  GRAPH_PATH,
  LEGACY_ASK_PATH,
  READER_PATH,
  WORKSPACE_PATH,
} from "../routes/paths.js";

export {
  buildStandaloneChatPath,
  buildStandaloneEvidencePath,
  buildStandaloneTracePath,
  buildTraceabilityParams,
  buildWorkspaceTracePath,
  describeTraceabilityState,
  legacyWorkspaceTabRedirectTarget,
  mergeTraceabilityParams,
  readTraceabilityState,
} from "../components/work/traceabilityState.js";
