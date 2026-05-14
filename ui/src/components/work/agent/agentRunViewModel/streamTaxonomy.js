/**
 * Taxonomy for live UX: what belongs in the main headline vs chips vs inspector-only.
 * @typedef {'primary' | 'secondary' | 'debug'} LiveStreamKind
 */

/** @type {Record<string, LiveStreamKind>} */
export const LIVE_STREAM_TAXONOMY = {
  product_step: "primary",
  warning: "primary",
  evidence_ready: "primary",
  context_compacted: "primary",
  specialist_selected: "primary",
  tool_search_result: "primary",
  intent_classified: "primary",
  subagent_started: "primary",
  subagent_progress: "secondary",
  subagent_finished: "primary",
  answer_synthesis_started: "primary",
  answer_synthesis_finished: "primary",
  degraded_mode: "primary",
  agent_note: "secondary",
  tool_call: "secondary",
  tool_result: "debug",
  error: "debug",
};

/**
 * @param {string} type
 * @returns {LiveStreamKind}
 */
export function liveStreamKindForType(type) {
  const k = String(type || "").trim();
  return LIVE_STREAM_TAXONOMY[k] || "debug";
}
