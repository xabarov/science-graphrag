/**
 * Single source of truth for translating raw backend enum codes
 * (e.g. `single_agent_react`, `low_signal`, `grounded_explanation`) into
 * user-facing labels via i18n. Sibling modules read from here so live UI
 * never shows snake_case identifiers when a known code is available.
 *
 * - Translation tables intentionally pre-declare every known value so that
 *   missing translations surface as test failures (see agentRunVocabulary.test.js).
 * - For unknown / future codes we fall back to {@link humanizeUnknownCode} which
 *   produces a readable but neutral string instead of leaking the raw token.
 *
 * `tool_search_result` is internal tool-catalog plumbing — {@link shouldHideStreamEventFromHeadline}
 * drops it from the live headline so users see intent / routing / product steps instead
 * of e.g. «Research agent · full toolset». {@link shouldOmitFromLiveRecentList} also removes
 * `tool_search_result` and per-row `tool_result` spam from the expandable «recent lines» list
 * (specialist run stack / inspector still show full detail).
 */

const SPECIALIST_KEYS = [
  "supervisor",
  "retrieval_agent",
  "graph_agent",
  "writer_agent",
  "single_agent_react",
];

const ANSWER_CLASS_KEYS = [
  "grounded_explanation",
  "fact_lookup",
  "inventory",
  "quote_extraction",
  "ideation",
  "bibliography_export",
  "synthesis",
  "relation_tracing",
];

const TOOL_SEARCH_REASON_KEYS = [
  "rules",
  "low_signal",
  "fallback_full",
  "fallback_full_single_agent",
  "disabled",
  "writer_minimal_set",
];

const ROUTE_REASON_KEYS = [
  "single_agent_research_runtime",
  "coordinator_route_hint",
  "semantic_fast_route",
  "supervisor_round_cap",
  "budget_exhausted",
  "coordinator_classifier_fallback",
];

const INTENT_SOURCE_KEYS = [
  "single_agent_research_v1",
  "coordinator_gate_v0",
  "heuristic",
  "deterministic",
  "shortcut",
];

/**
 * Source labels considered redundant for end-users (always the runtime default
 * for a given route). We hide them from the live headline so the UI shows just
 * the answer class instead of `Intent: grounded_explanation (single_agent_research_v1)`.
 */
const REDUNDANT_INTENT_SOURCES = new Set(["single_agent_research_v1", "coordinator_gate_v0"]);

/**
 * Convert an unknown `snake_case` / `kebab-case` / `dotted` code into a plain
 * readable sentence: `single_agent_research_runtime` →
 * `Single agent research runtime`.
 *
 * If the input already looks like prose (contains a whitespace character) we
 * return it unchanged so we never destroy a backend-provided sentence such as
 * `Classified as catalog-style question.`.
 *
 * @param {unknown} code
 * @returns {string}
 */
export function humanizeUnknownCode(code) {
  const raw = String(code ?? "").trim();
  if (!raw) return "";
  if (/\s/.test(raw)) return raw;
  const cleaned = raw.replace(/[._\-:]+/g, " ").replace(/\s+/g, " ").trim();
  if (!cleaned) return "";
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1).toLowerCase();
}

/**
 * @param {(key: string, vars?: Record<string, string>) => string} t
 * @param {string} i18nKey
 * @param {string} rawCode
 * @returns {string}
 */
function translateOrFallback(t, i18nKey, rawCode) {
  const out = t(i18nKey);
  if (out && out !== i18nKey) return out;
  return humanizeUnknownCode(rawCode);
}

/**
 * Map specialist / agent role identifiers to human labels.
 *
 * @param {(key: string, vars?: Record<string, string>) => string} t
 * @param {unknown} name
 * @returns {string}
 */
export function mapSpecialistToLabel(t, name) {
  const code = String(name ?? "").trim();
  if (!code) return "";
  return translateOrFallback(t, `chat.run.specialist.${code}`, code);
}

/**
 * Map normalized `answer_class` enum to a localized label.
 *
 * @param {(key: string, vars?: Record<string, string>) => string} t
 * @param {unknown} cls
 * @returns {string}
 */
export function mapAnswerClassToLabel(t, cls) {
  const code = String(cls ?? "").trim();
  if (!code) return "";
  return translateOrFallback(t, `chat.run.answerClass.${code}`, code);
}

/**
 * Map `tool_search_result.reason` to a localized label.
 *
 * @param {(key: string, vars?: Record<string, string>) => string} t
 * @param {unknown} reason
 * @returns {string}
 */
export function mapToolSearchReasonToLabel(t, reason) {
  const code = String(reason ?? "").trim();
  if (!code) return "";
  return translateOrFallback(t, `chat.run.toolSearchReason.${code}`, code);
}

/**
 * Map routing-log `reason` (also `subagent_progress.summary` source) to a label.
 *
 * @param {(key: string, vars?: Record<string, string>) => string} t
 * @param {unknown} reason
 * @returns {string}
 */
export function mapRouteReasonToLabel(t, reason) {
  const code = String(reason ?? "").trim();
  if (!code) return "";
  return translateOrFallback(t, `chat.run.routeReason.${code}`, code);
}

/**
 * Map `intent_classified.source` to a label, or empty string if the source is
 * a redundant default (e.g. `single_agent_research_v1`).
 *
 * @param {(key: string, vars?: Record<string, string>) => string} t
 * @param {unknown} src
 * @returns {string}
 */
export function mapIntentSourceToLabel(t, src) {
  const code = String(src ?? "").trim();
  if (!code) return "";
  if (isRedundantIntentSource(code)) return "";
  return translateOrFallback(t, `chat.run.intentSource.${code}`, code);
}

/**
 * Map structured stream `error.code` to a localized message. Falls back to
 * `humanizeUnknownCode` so unknown codes still render readably.
 *
 * @param {(key: string, vars?: Record<string, string>) => string} t
 * @param {unknown} code
 * @returns {string}
 */
export function mapErrorCodeToLabel(t, code) {
  const raw = String(code ?? "").trim();
  if (!raw) return "";
  return translateOrFallback(t, `chat.errors.${raw}`, raw);
}

/**
 * @param {string} src
 * @returns {boolean}
 */
export function isRedundantIntentSource(src) {
  return REDUNDANT_INTENT_SOURCES.has(String(src ?? "").trim());
}

/**
 * Whether a stream event should be suppressed from the *headline* (live card
 * primary line). Such events still appear in expanded recent-line history and
 * inspector trace.
 *
 * @param {unknown} event
 * @returns {boolean}
 */
export function shouldHideStreamEventFromHeadline(event) {
  if (!event || typeof event !== "object") return false;
  const ev = /** @type {Record<string, unknown>} */ (event);
  const type = String(ev.type || "");
  if (type === "tool_search_result") return true;
  return false;
}

/**
 * Omit noisy / redundant event types from the live card's «recent lines» list only.
 * Keeps chips + headline focused on product-facing steps; avoids repeating every
 * `tool_result` row count line.
 *
 * @param {unknown} event
 * @returns {boolean}
 */
export function shouldOmitFromLiveRecentList(event) {
  if (!event || typeof event !== "object") return false;
  const type = String(/** @type {Record<string, unknown>} */ (event).type || "");
  return type === "tool_result" || type === "tool_search_result";
}

export const __VOCAB_KEYS = {
  SPECIALIST_KEYS,
  ANSWER_CLASS_KEYS,
  TOOL_SEARCH_REASON_KEYS,
  ROUTE_REASON_KEYS,
  INTENT_SOURCE_KEYS,
};
