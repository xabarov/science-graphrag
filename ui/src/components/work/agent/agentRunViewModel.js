/**
 * Presentation-only helpers for agent chat run chrome (no transport changes).
 *
 * Live UX phases (rollout / fallback):
 * - Primary: `buildLiveStatusPresentation` headline + optional activity chips while streaming.
 * - Secondary: safe explanation lines (reason/summary only; no raw tool args).
 * - Fallback: if explanations are disabled or empty, inspector + recent lines still carry detail.
 *
 * Raw enum codes from the SSE stream are translated to user-facing labels via
 * `agentRunVocabulary.js` so the headline / recent-line history never shows
 * snake_case identifiers like `single_agent_react` or `low_signal`.
 *
 * Implementation is split under `./agentRunViewModel/`; this file is a stable re-export surface.
 */

export { LIVE_STREAM_TAXONOMY, liveStreamKindForType } from "./agentRunViewModel/streamTaxonomy.js";
export { mapToolNameToUserLabel, formatStreamEventOneLine } from "./agentRunViewModel/streamFormat.js";
export {
  getEventGroupKey,
  aggregateRepeatedEvents,
  formatAggregatedEventOneLine,
  collectFormattedStreamLines,
  collectRecentToolNamesForChips,
} from "./agentRunViewModel/streamAggregation.js";
export {
  pickLastMeaningfulStreamEvent,
  PRODUCT_STEP_HEADLINE_STALE_MS,
  pickPrimaryHeadlineEvent,
  derivePrimaryHeadline,
  pickLastToolCallEvent,
} from "./agentRunViewModel/streamHeadline.js";
export { deriveProgressHint } from "./agentRunViewModel/progress.js";
export { deriveDecisionRationale, collectSafeExplanationLines, pickLatestAgentNote } from "./agentRunViewModel/explanations.js";
export {
  shouldSuppressPostRunStreamSummary,
  buildLiveStatusPresentation,
  deriveHeaderProgressHint,
  buildSpecialistStreamGroups,
  shouldShowSubagentRail,
} from "./agentRunViewModel/presentation.js";
export { deriveRunState, shouldOfferRunInspector } from "./agentRunViewModel/runState.js";
