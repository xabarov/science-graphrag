import { mapAnswerClassToLabel, mapSpecialistToLabel, shouldHideStreamEventFromHeadline } from "../agentRunVocabulary.js";
import {
  aggregateRepeatedEvents,
  formatAggregatedEventOneLine,
  getEventGroupKey,
} from "./streamAggregation.js";
import { formatStreamEventOneLine } from "./streamFormat.js";

/** Product-facing stream signals only (tool_call/tool_result stay in inspector). */
const MEANINGFUL_STREAM_TYPES = new Set([
  "warning",
  "evidence_ready",
  "context_compacted",
  "specialist_selected",
  "tool_search_result",
  "intent_classified",
  "subagent_started",
  "subagent_progress",
  "subagent_finished",
  "answer_synthesis_started",
  "answer_synthesis_finished",
  "degraded_mode",
  "product_step",
  "agent_note",
]);

/**
 * @param {unknown[]} events
 * @returns {Record<string, unknown> | null}
 */
export function pickLastMeaningfulStreamEvent(events) {
  if (!Array.isArray(events) || events.length === 0) return null;
  for (let i = events.length - 1; i >= 0; i -= 1) {
    const ev = events[i];
    if (!ev || typeof ev !== "object") continue;
    const type = String(ev.type || "");
    if (!MEANINGFUL_STREAM_TYPES.has(type)) continue;
    if (shouldHideStreamEventFromHeadline(ev)) continue;
    return ev;
  }
  return null;
}

/** Ignore headline `product_step` older than this vs newest stamped `_receivedAtMs` (live streams only). */
export const PRODUCT_STEP_HEADLINE_STALE_MS = 8000;

const HEADLINE_PRIORITY = {
  degraded_mode: 7,
  product_step: 6,
  answer_synthesis_finished: 5,
  answer_synthesis_started: 5,
  subagent_started: 4,
  subagent_finished: 4,
  evidence_ready: 3,
  context_compacted: 3,
  specialist_selected: 3,
  intent_classified: 2,
  warning: 1,
  tool_call: 1,
};

/**
 * Pick the strongest "voice" event for the live headline.
 *
 * Priority (high → low): `degraded_mode` → active `product_step` (most recent) → `answer_synthesis_*` →
 * `subagent_started/finished` → `evidence_ready` / `context_compacted` /
 * `specialist_selected` → `intent_classified` → most recent `tool_call` /
 * `warning`. Within the same priority level, the latest event wins.
 *
 * @param {unknown[]} events
 * @returns {Record<string, unknown> | null}
 */
export function pickPrimaryHeadlineEvent(events) {
  if (!Array.isArray(events) || events.length === 0) return null;
  const last = events[events.length - 1];
  const refMs =
    last && typeof last === "object" && typeof /** @type {{ _receivedAtMs?: unknown }} */ (last)._receivedAtMs === "number"
      ? /** @type {{ _receivedAtMs: number }} */ (last)._receivedAtMs
      : null;
  const useFreshness = refMs !== null;
  /** @type {{ ev: Record<string, unknown>, prio: number, idx: number } | null} */
  let best = null;
  for (let i = 0; i < events.length; i += 1) {
    const ev = events[i];
    if (!ev || typeof ev !== "object") continue;
    const type = String(ev.type || "");
    if (!MEANINGFUL_STREAM_TYPES.has(type) && type !== "tool_call") continue;
    if (shouldHideStreamEventFromHeadline(ev)) continue;
    let prio = HEADLINE_PRIORITY[type] || 0;
    if (
      useFreshness &&
      type === "product_step" &&
      typeof /** @type {{ _receivedAtMs?: unknown }} */ (ev)._receivedAtMs === "number" &&
      refMs - /** @type {{ _receivedAtMs: number }} */ (ev)._receivedAtMs > PRODUCT_STEP_HEADLINE_STALE_MS
    ) {
      prio = 0;
    }
    if (prio === 0) continue;
    if (!best || prio > best.prio || (prio === best.prio && i > best.idx)) {
      best = { ev: /** @type {Record<string, unknown>} */ (ev), prio, idx: i };
    }
  }
  return best ? best.ev : null;
}

/**
 * Single active-voice headline for the live card. Always returns a non-empty
 * localized phrase: a product-step / synthesis / subagent line, or an
 * "interpreting question" placeholder for early `intent_classified` events,
 * or `chat.stream.thinking` as a final fallback when streaming is active.
 *
 * @param {(key: string, vars?: Record<string, string>) => string} t
 * @param {unknown[]} events
 * @param {boolean} isRunActive
 * @returns {string}
 */
export function derivePrimaryHeadline(t, events, isRunActive) {
  const list = Array.isArray(events) ? events : [];
  const ev = pickPrimaryHeadlineEvent(list);
  if (ev) {
    const type = String(ev.type || "");
    if (type === "intent_classified") {
      const clsRaw = String(ev.answer_class || "");
      const clsLabel = mapAnswerClassToLabel(t, clsRaw) || clsRaw;
      const phrase = t("chat.run.headline.thinkingAbout", { cls: clsLabel });
      if (phrase && phrase !== "chat.run.headline.thinkingAbout") return phrase;
    }
    if (type === "subagent_started") {
      const idRaw = String(ev.subagent_id || ev.name || "");
      const idLabel = mapSpecialistToLabel(t, idRaw) || idRaw;
      const phrase = t("chat.run.headline.delegatedTo", { id: idLabel });
      if (phrase && phrase !== "chat.run.headline.delegatedTo") return phrase;
    }
    const formatted = formatStreamEventOneLine(t, ev);
    if (formatted) {
      const groupKey = getEventGroupKey(ev);
      if (groupKey) {
        const aggregated = aggregateRepeatedEvents(list);
        const trailing = aggregated.length > 0 ? aggregated[aggregated.length - 1] : null;
        if (trailing && getEventGroupKey(trailing.event) === groupKey && trailing.count > 1) {
          return formatAggregatedEventOneLine(t, trailing);
        }
      }
      return formatted;
    }
  }
  if (isRunActive) return t("chat.stream.thinking");
  return "";
}

/**
 * @param {unknown[]} events
 * @returns {Record<string, unknown> | null}
 */
export function pickLastToolCallEvent(events) {
  if (!Array.isArray(events) || events.length === 0) return null;
  for (let i = events.length - 1; i >= 0; i -= 1) {
    const ev = events[i];
    if (!ev || typeof ev !== "object") continue;
    if (String(ev.type || "") === "tool_call") return ev;
  }
  return null;
}
