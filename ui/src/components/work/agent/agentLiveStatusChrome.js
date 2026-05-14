/**
 * Apply Ask/chat detail level and embedded-rail chrome rules on top of the
 * presentation model from `buildLiveStatusPresentation`.
 *
 * @param {{
 *   activityChips?: unknown,
 *   showRecentToggle?: boolean,
 *   showExplainToggle?: boolean,
 * }} presentation
 * @param {{ chatDetailLevel: "simple" | "detailed", embedded: boolean }} opts
 * @returns {{
 *   isSimple: boolean,
 *   minimalEmbeddedChrome: boolean,
 *   activityChips: Array<{ tool: string, label: string }>,
 *   showRecentToggle: boolean,
 *   showExplainToggle: boolean,
 * }}
 */
export function deriveAgentLiveStatusChrome(presentation, { chatDetailLevel, embedded }) {
  const isSimple = chatDetailLevel !== "detailed";
  const minimalEmbeddedChrome = Boolean(embedded);
  if (!presentation || typeof presentation !== "object") {
    return {
      isSimple,
      minimalEmbeddedChrome,
      activityChips: [],
      showRecentToggle: false,
      showExplainToggle: false,
    };
  }
  const rawChips = Array.isArray(presentation.activityChips) ? presentation.activityChips : [];
  const activityChips = minimalEmbeddedChrome ? [] : isSimple ? rawChips.slice(0, 2) : rawChips;
  return {
    isSimple,
    minimalEmbeddedChrome,
    activityChips,
    showRecentToggle: Boolean(!isSimple && presentation.showRecentToggle),
    showExplainToggle: Boolean(!isSimple && presentation.showExplainToggle),
  };
}
