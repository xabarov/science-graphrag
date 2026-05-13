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
 */

import {
  humanizeUnknownCode,
  isHiddenFromSpecialistRunTrace,
  isRedundantIntentSource,
  mapAnswerClassToLabel,
  mapErrorCodeToLabel,
  mapIntentSourceToLabel,
  mapRouteReasonToLabel,
  mapSpecialistToLabel,
  mapToolSearchReasonToLabel,
  shouldHideStreamEventFromHeadline,
  shouldOmitFromLiveRecentList,
} from "./agentRunVocabulary.js";

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

/**
 * User-facing tool label (i18n). Falls back to a generic pattern for unknown tools.
 *
 * @param {(key: string, vars?: Record<string, string>) => string} t
 * @param {string} toolName
 * @returns {string}
 */
export function mapToolNameToUserLabel(t, toolName) {
  const tool = String(toolName || "").trim() || "tool";
  const key = `chat.run.toolLabel.${tool}`;
  const out = t(key);
  return out === key ? t("chat.run.toolLabel.generic", { tool }) : out;
}

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

/**
 * @param {(key: string, vars?: Record<string, string>) => string} t
 * @param {Record<string, unknown> | null} event
 * @returns {string}
 */
export function formatStreamEventOneLine(t, event) {
  if (!event || typeof event !== "object") return "";
  const type = String(event.type || "");
  if (type === "tool_call") {
    const tool = String(event.tool || "tool");
    const q =
      event.args_summary && typeof event.args_summary === "object" && event.args_summary.query != null
        ? String(event.args_summary.query).slice(0, 48)
        : "";
    const label = mapToolNameToUserLabel(t, tool);
    return q
      ? t("chat.run.live.toolCallQuery", { tool: label, q: `"${q}${q.length >= 48 ? "…" : ""}"` })
      : t("chat.run.live.toolCall", { tool: label });
  }
  if (type === "tool_result") {
    const err = event.error ? String(event.error) : "";
    const parts = [
      `${t("chat.stream.toolResultLabel")}: ${mapToolNameToUserLabel(t, String(event.tool || ""))}`,
      event.row_count != null ? `${t("chat.stream.rowsLabel")}: ${String(event.row_count)}` : null,
      err ? `${t("chat.stream.errorLabel")}: ${err.slice(0, 100)}` : null,
    ].filter(Boolean);
    return parts.join(" · ");
  }
  if (type === "intent_classified") {
    const clsRaw = String(event.answer_class || "");
    const clsLabel = mapAnswerClassToLabel(t, clsRaw);
    const cls = clsLabel || clsRaw;
    const srcRaw = String(event.source || "");
    if (!srcRaw || isRedundantIntentSource(srcRaw)) {
      return t("chat.stream.intentNoSource", { cls });
    }
    const srcLabel = mapIntentSourceToLabel(t, srcRaw) || humanizeUnknownCode(srcRaw);
    return t("chat.stream.intent", { cls, src: srcLabel });
  }
  if (type === "specialist_selected") {
    const fr = mapSpecialistToLabel(t, event.from) || String(event.from || "");
    const to = mapSpecialistToLabel(t, event.to) || String(event.to || "");
    return t("chat.stream.route", { fr, to });
  }
  if (type === "tool_search_result") {
    const specRaw = String(event.specialist || "");
    const spec = mapSpecialistToLabel(t, specRaw) || specRaw;
    const reasonRaw = String(event.reason || "");
    const reason = mapToolSearchReasonToLabel(t, reasonRaw);
    if (event.skipped) {
      return t("chat.stream.toolSearchSkipped", { spec });
    }
    return t("chat.stream.toolSearch", { spec, reason: reason || reasonRaw });
  }
  if (type === "evidence_ready") {
    return t("chat.stream.evidenceReady", { n: String(event.citation_count ?? "") });
  }
  if (type === "context_compacted") {
    return t("chat.stream.contextCompacted");
  }
  if (type === "warning") {
    const code = String(event.code || "");
    const message = String(event.message || "").slice(0, 180);
    const i18nKey = code ? `chat.warnings.${code}` : "";
    const localized = i18nKey ? t(i18nKey) : "";
    if (localized && localized !== i18nKey) {
      return t("chat.stream.warningLine", { message: localized });
    }
    if (message) {
      const label = code ? humanizeUnknownCode(code) : "";
      return label
        ? t("chat.stream.warningLineWithCode", { label, message })
        : t("chat.stream.warningLine", { message });
    }
    if (code) {
      return t("chat.stream.warningLine", { message: humanizeUnknownCode(code) });
    }
    return "";
  }
  if (type === "subagent_started") {
    const idRaw = String(event.subagent_id || event.name || "");
    const id = mapSpecialistToLabel(t, idRaw) || idRaw;
    const spawnReason = String(event.spawn_reason || "");
    const kind = String(event.kind || "");
    const taskType = String(event.task_type || "");
    const isSpawned = kind === "spawned" || Boolean(taskType);
    const detail = isSpawned ? t("chat.stream.subagentKind.spawned") : t("chat.stream.subagentKind.routing");
    const reason = mapRouteReasonToLabel(t, spawnReason) || spawnReason;
    return reason
      ? t("chat.stream.subagentStartedDetailed", { id, detail, reason })
      : t("chat.stream.subagentStarted", { id });
  }
  if (type === "subagent_progress") {
    const idRaw = String(event.subagent_id || "");
    const id = mapSpecialistToLabel(t, idRaw) || idRaw;
    const rawSummary = String(event.summary || event.tool || "");
    const tool = String(event.tool || "");
    let summary;
    if (tool && rawSummary === tool) {
      summary = mapToolNameToUserLabel(t, tool);
    } else {
      const reasonLabel = mapRouteReasonToLabel(t, rawSummary);
      summary = reasonLabel || rawSummary.slice(0, 120);
    }
    return t("chat.stream.subagentProgress", { id, summary });
  }
  if (type === "subagent_finished") {
    const idRaw = String(event.subagent_id || "");
    const id = mapSpecialistToLabel(t, idRaw) || idRaw;
    const terminalState = String(event.terminal_state || "").trim();
    const stateKey = terminalState ? `chat.stream.subagentTerminal.${terminalState}` : "";
    const stateLabel = stateKey ? t(stateKey) : "";
    const provenance = event.merge_provenance && typeof event.merge_provenance === "object"
      ? String(event.merge_provenance.source_kind || event.merge_provenance.evidence_origin || "").trim()
      : "";
    if (stateLabel && provenance) {
      return t("chat.stream.subagentFinishedDetailed", { id, state: stateLabel, provenance });
    }
    if (stateLabel) {
      return t("chat.stream.subagentFinishedStateOnly", { id, state: stateLabel });
    }
    return t("chat.stream.subagentFinished", { id });
  }
  if (type === "answer_synthesis_started") {
    return t("chat.stream.answerSynthesisStarted");
  }
  if (type === "answer_synthesis_finished") {
    return t("chat.stream.answerSynthesisFinished");
  }
  if (type === "degraded_mode") {
    const reasons = Array.isArray(event.reasons) ? event.reasons : [];
    if (reasons.length === 0) return "";
    const parts = reasons
      .map((raw) => {
        const r = String(raw ?? "").trim();
        if (!r) return "";
        const key = `chat.stream.degradedReason.${r}`;
        const out = t(key);
        return out === key ? humanizeUnknownCode(r) : out;
      })
      .filter(Boolean);
    return parts.join(" · ");
  }
  if (type === "product_step") {
    const code = String(event.code || "");
    if (code === "using_tool") {
      const tool = String(event.tool || "").trim() || "tool";
      return t("chat.run.productStep.using_tool", { tool: mapToolNameToUserLabel(t, tool) });
    }
    const key = `chat.run.productStep.${code}`;
    const out = t(key);
    return out === key ? humanizeUnknownCode(code) : out;
  }
  if (type === "agent_note") {
    const note = String(event.note || "").trim();
    if (!note) return "";
    return t("chat.stream.agentNote", { note });
  }
  if (type === "final_answer") {
    const out = t("chat.stream.finalAnswerEnvelope");
    return out === "chat.stream.finalAnswerEnvelope" ? "" : out;
  }
  if (type === "error") {
    const errorClass = String(event.error_class || "");
    const code = String(event.code || "");
    const message = String(event.message || event.detail || "").trim();
    const classified = errorClass ? mapErrorCodeToLabel(t, errorClass) : "";
    if (classified) {
      return message && !message.startsWith(classified) ? `${classified} · ${message.slice(0, 200)}` : classified;
    }
    const codeLabel = code ? mapErrorCodeToLabel(t, code) : "";
    if (codeLabel) {
      return message ? `${codeLabel} · ${message.slice(0, 200)}` : codeLabel;
    }
    if (message) return message.slice(0, 240);
    if (errorClass) return humanizeUnknownCode(errorClass);
    return code ? humanizeUnknownCode(code) : "";
  }
  return "";
}

/**
 * Short user-facing line for the run header while streaming (meaningful steps only).
 *
 * @param {(key: string, vars?: Record<string, string>) => string} t
 * @param {unknown[]} streamEvents
 * @param {boolean} isRunActive
 * @returns {string}
 */
export function deriveProgressHint(t, streamEvents, isRunActive) {
  if (!isRunActive) return "";
  const ev = pickLastMeaningfulStreamEvent(streamEvents);
  const line = formatStreamEventOneLine(t, ev);
  if (line) return line;
  const tc = pickLastToolCallEvent(streamEvents);
  if (tc) {
    const toolLine = formatStreamEventOneLine(t, tc);
    if (toolLine) return toolLine;
  }
  return t("chat.run.progressWorking");
}

/**
 * Stable group key for aggregation: events with the same key fold into one
 * "(×N)" line when adjacent. Returns empty string when an event must not be
 * aggregated.
 *
 * @param {unknown} event
 * @returns {string}
 */
export function getEventGroupKey(event) {
  if (!event || typeof event !== "object") return "";
  const ev = /** @type {Record<string, unknown>} */ (event);
  const type = String(ev.type || "");
  if (type === "tool_call") {
    const tool = String(ev.tool || "").trim();
    return tool ? `tool_call:${tool}` : "";
  }
  if (type === "product_step") {
    const code = String(ev.code || "").trim();
    if (!code) return "";
    if (code === "using_tool") {
      const tool = String(ev.tool || "").trim();
      return tool ? `product_step:using_tool:${tool}` : "product_step:using_tool";
    }
    return `product_step:${code}`;
  }
  return "";
}

/**
 * @typedef {{
 *   kind: "single" | "group",
 *   event: Record<string, unknown>,
 *   count: number,
 *   firstIdx: number,
 *   lastIdx: number,
 * }} AggregatedEvent
 */

/**
 * Collapse adjacent repeats of the same `tool_call` / `product_step` into a
 * single virtual event with `count`. Non-aggregatable events pass through as
 * `{ kind: "single", count: 1 }`. The order of underlying events is preserved.
 *
 * @param {unknown[]} events
 * @returns {AggregatedEvent[]}
 */
export function aggregateRepeatedEvents(events) {
  if (!Array.isArray(events) || events.length === 0) return [];
  /** @type {AggregatedEvent[]} */
  const out = [];
  for (let i = 0; i < events.length; i += 1) {
    const ev = events[i];
    if (!ev || typeof ev !== "object") continue;
    const obj = /** @type {Record<string, unknown>} */ (ev);
    const key = getEventGroupKey(obj);
    if (!key) {
      out.push({ kind: "single", event: obj, count: 1, firstIdx: i, lastIdx: i });
      continue;
    }
    const last = out.length > 0 ? out[out.length - 1] : null;
    if (last && getEventGroupKey(last.event) === key) {
      last.kind = "group";
      last.count += 1;
      last.lastIdx = i;
      continue;
    }
    out.push({ kind: "single", event: obj, count: 1, firstIdx: i, lastIdx: i });
  }
  return out;
}

/**
 * Format an aggregated entry. Single entries delegate to
 * `formatStreamEventOneLine`; groups append `(×N)` via the
 * `chat.run.headline.repeatedSuffix` template.
 *
 * @param {(key: string, vars?: Record<string, string>) => string} t
 * @param {AggregatedEvent} entry
 * @returns {string}
 */
export function formatAggregatedEventOneLine(t, entry) {
  if (!entry || typeof entry !== "object") return "";
  const base = formatStreamEventOneLine(t, entry.event);
  if (!base) return "";
  if (entry.count <= 1) return base;
  const ev = /** @type {Record<string, unknown>} */ (entry.event);
  const type = ev && typeof ev === "object" ? String(ev.type || "") : "";
  const key =
    type === "tool_call"
      ? "chat.run.live.toolCallRepeated"
      : type === "product_step"
        ? "chat.run.live.productStepRepeated"
        : "chat.run.headline.repeatedSuffix";
  const vars = { base, count: String(entry.count) };
  const out = t(key, vars);
  return out === key ? t("chat.run.headline.repeatedSuffix", vars) : out;
}

/**
 * One formatted line per event (chronological), for expandable live status.
 * Adjacent repeats of `tool_call` / `product_step` are collapsed into a single
 * "(×N)" line so long bursts do not flood the recent list.
 *
 * @param {(key: string, vars?: Record<string, string>) => string} t
 * @param {unknown[]} events
 * @param {number} [limit]
 * @returns {string[]}
 */
export function collectFormattedStreamLines(t, events, limit = 24) {
  if (!Array.isArray(events) || events.length === 0) return [];
  const aggregated = aggregateRepeatedEvents(events);
  const lines = [];
  for (const entry of aggregated) {
    const line = formatAggregatedEventOneLine(t, entry);
    if (line) lines.push(line);
  }
  if (lines.length <= limit) return lines;
  return lines.slice(-limit);
}

/**
 * @param {unknown[]} events
 * @param {number} [maxChips]
 * @returns {string[]}
 */
export function collectRecentToolNamesForChips(events, maxChips = 4) {
  if (!Array.isArray(events) || events.length === 0) return [];
  /** @type {string[]} */
  const ordered = [];
  for (const ev of events) {
    if (!ev || typeof ev !== "object") continue;
    if (String(ev.type || "") !== "tool_call") continue;
    const name = String(ev.tool || "").trim();
    if (!name) continue;
    const normalized = name.toLowerCase().replace(/-/g, "_");
    if (normalized === "final_answer") continue;
    ordered.push(name);
  }
  if (ordered.length === 0) return [];
  const tail = ordered.slice(-12);
  /** @type {string[]} */
  const out = [];
  for (let i = tail.length - 1; i >= 0 && out.length < maxChips; i -= 1) {
    const n = tail[i];
    if (!out.includes(n)) out.push(n);
  }
  return out;
}

/**
 * Compact "Decision / Why" block above the headline. Uses the latest
 * `intent_classified` (decision = answer class) and the most informative
 * `reason` (intent reason → routing reason). Skips redundant defaults like
 * `single_agent_research_runtime` so the row is only shown when useful.
 *
 * @param {(key: string, vars?: Record<string, string>) => string} t
 * @param {unknown[]} events
 * @returns {{ decision: string, why: string }}
 */
export function deriveDecisionRationale(t, events) {
  if (!Array.isArray(events) || events.length === 0) return { decision: "", why: "" };
  /** @type {Record<string, unknown> | null} */
  let lastIntent = null;
  /** @type {Record<string, unknown> | null} */
  let lastSpecialist = null;
  for (const ev of events) {
    if (!ev || typeof ev !== "object") continue;
    const type = String(ev.type || "");
    if (type === "intent_classified") lastIntent = /** @type {Record<string, unknown>} */ (ev);
    else if (type === "specialist_selected") lastSpecialist = /** @type {Record<string, unknown>} */ (ev);
  }
  let decision = "";
  if (lastIntent) {
    const clsRaw = String(lastIntent.answer_class || "");
    decision = mapAnswerClassToLabel(t, clsRaw) || (clsRaw ? humanizeUnknownCode(clsRaw) : "");
  }
  let why = "";
  const rawReason = String((lastIntent && lastIntent.reason) || (lastSpecialist && lastSpecialist.reason) || "").trim();
  if (rawReason && rawReason !== "single_agent_research_runtime") {
    const mapped = mapRouteReasonToLabel(t, rawReason);
    why = mapped || humanizeUnknownCode(rawReason);
  }
  return { decision, why };
}

/**
 * Safe, short "how it is working" lines (no raw args_summary, no debug_events).
 *
 * When `excludeKinds` includes `"decision"`, route-reason and intent-reason lines
 * are skipped so the same content is not duplicated under a separate
 * "Decision / Why" block.
 *
 * @param {(key: string, vars?: Record<string, string>) => string} t
 * @param {unknown[]} events
 * @param {number} [maxLines]
 * @param {{ excludeKinds?: string[] }} [opts]
 * @returns {string[]}
 */
export function collectSafeExplanationLines(t, events, maxLines = 6, opts = {}) {
  if (!Array.isArray(events) || events.length === 0) return [];
  const exclude = new Set((opts && Array.isArray(opts.excludeKinds) ? opts.excludeKinds : []).map(String));
  const skipDecision = exclude.has("decision");
  /** @type {string[]} */
  const raw = [];
  for (const ev of events) {
    if (!ev || typeof ev !== "object") continue;
    const type = String(ev.type || "");
    if (type === "specialist_selected") {
      if (skipDecision) continue;
      const reasonRaw = String(ev.reason || "").trim();
      if (reasonRaw) {
        const reason = mapRouteReasonToLabel(t, reasonRaw) || reasonRaw.slice(0, 160);
        raw.push(t("chat.run.liveExplain.routeReason", { reason }));
      }
    } else if (type === "intent_classified") {
      if (skipDecision) continue;
      const reasonRaw = String(ev.reason || "").trim();
      if (reasonRaw) {
        const reason = mapRouteReasonToLabel(t, reasonRaw) || reasonRaw.slice(0, 160);
        const clsRaw = String(ev.answer_class || "");
        const cls = mapAnswerClassToLabel(t, clsRaw) || clsRaw;
        raw.push(t("chat.run.liveExplain.intentReason", { cls, reason }));
      }
    } else if (type === "subagent_started") {
      const summaryRaw = String(ev.summary || "").trim();
      if (summaryRaw) {
        const idRaw = String(ev.subagent_id || "");
        const id = mapSpecialistToLabel(t, idRaw) || idRaw;
        const summary = mapRouteReasonToLabel(t, summaryRaw) || summaryRaw.slice(0, 160);
        raw.push(t("chat.run.liveExplain.subagentSummary", { id, summary }));
      }
    } else if (type === "subagent_finished") {
      const idRaw = String(ev.subagent_id || "");
      const id = mapSpecialistToLabel(t, idRaw) || idRaw;
      const terminalState = String(ev.terminal_state || "").trim();
      const provenance =
        ev.merge_provenance && typeof ev.merge_provenance === "object"
          ? String(ev.merge_provenance.source_kind || ev.merge_provenance.evidence_origin || "").trim()
          : "";
      if (terminalState || provenance) {
        raw.push(
          t("chat.run.liveExplain.subagentOutcome", {
            id,
            state: terminalState || "unknown",
            provenance: provenance || "none",
          }),
        );
      }
    }
  }
  const tail = raw.slice(-maxLines * 2);
  /** @type {string[]} */
  const deduped = [];
  for (const line of tail) {
    if (deduped.length && deduped[deduped.length - 1] === line) continue;
    deduped.push(line);
  }
  return deduped.slice(-maxLines);
}

/**
 * @typedef {{
 *   headline: string,
 *   decision: string,
 *   why: string,
 *   latestAgentNote: string,
 *   activityChips: Array<{ tool: string, label: string }>,
 *   explanations: string[],
 *   recentLines: string[],
 *   showRecentToggle: boolean,
 *   showExplainToggle: boolean,
 * }} LiveStatusPresentation
 */

/**
 * Latest non-empty `agent_note` text from the stream, or empty string.
 *
 * @param {unknown[]} events
 * @returns {string}
 */
export function pickLatestAgentNote(events) {
  if (!Array.isArray(events) || events.length === 0) return "";
  for (let i = events.length - 1; i >= 0; i -= 1) {
    const ev = events[i];
    if (!ev || typeof ev !== "object") continue;
    if (String(ev.type || "") !== "agent_note") continue;
    const note = String(ev.note || "").trim();
    if (note) return note;
  }
  return "";
}

/**
 * Single source of truth for the live-run card (headline, chips, explanations, recent list).
 *
 * @param {(key: string, vars?: Record<string, string>) => string} t
 * @param {unknown[]} streamEvents
 * @param {boolean} isRunActive
 * @returns {LiveStatusPresentation}
 */
/**
 * After a completed run, suppress the post-run headline when it only repeats
 * the redundant "answer ready" line already implied by the answer section below.
 *
 * @param {unknown[]} streamEvents
 * @returns {boolean}
 */
export function shouldSuppressPostRunStreamSummary(streamEvents) {
  const ev = pickLastMeaningfulStreamEvent(streamEvents);
  if (!ev || typeof ev !== "object") return false;
  return String(/** @type {{ type?: string }} */ (ev).type || "") === "answer_synthesis_finished";
}

export function buildLiveStatusPresentation(t, streamEvents, isRunActive) {
  const list = Array.isArray(streamEvents) ? streamEvents : [];
  let headline = derivePrimaryHeadline(t, list, isRunActive);
  if (!headline && !isRunActive) {
    const meaningful = pickLastMeaningfulStreamEvent(list);
    if (meaningful) headline = formatStreamEventOneLine(t, meaningful);
    if (!headline) {
      const tc = pickLastToolCallEvent(list);
      headline = tc ? formatStreamEventOneLine(t, tc) : "";
    }
  }
  const toolNames = isRunActive ? collectRecentToolNamesForChips(list, 4) : [];
  let activityChips = toolNames.map((tool) => ({ tool, label: mapToolNameToUserLabel(t, tool) }));
  if (headline) {
    activityChips = activityChips.filter((chip) => chip.label.trim() !== headline.trim());
  }
  const { decision, why } = deriveDecisionRationale(t, list);
  const latestAgentNote = pickLatestAgentNote(list);
  const explanations = isRunActive
    ? collectSafeExplanationLines(t, list, 6, { excludeKinds: decision || why ? ["decision"] : [] })
    : [];

  const forRecent = list.filter((e) => e && typeof e === "object" && !shouldOmitFromLiveRecentList(e));
  const allLines = collectFormattedStreamLines(t, forRecent, 32);
  const recentLines = headline ? allLines.filter((line) => line !== headline) : allLines;

  const rawCount = list.filter((e) => e && typeof e === "object").length;
  const showRecentToggle = rawCount >= 2 && recentLines.length > 0;
  const showExplainToggle = explanations.length > 0;

  if (!isRunActive && !headline) {
    return {
      headline: "",
      decision: "",
      why: "",
      latestAgentNote: "",
      activityChips: [],
      explanations: [],
      recentLines: [],
      showRecentToggle: false,
      showExplainToggle: false,
    };
  }

  return {
    headline,
    decision,
    why,
    latestAgentNote,
    activityChips,
    explanations,
    recentLines,
    showRecentToggle,
    showExplainToggle,
  };
}

/**
 * Compact header hint while streaming: avoids duplicating the same line as the live card headline.
 *
 * @param {(key: string, vars?: Record<string, string>) => string} t
 * @param {unknown[]} streamEvents
 * @param {boolean} isRunActive
 * @returns {string}
 */
export function deriveHeaderProgressHint(t, streamEvents, isRunActive) {
  if (!isRunActive) return "";
  const pres = buildLiveStatusPresentation(t, streamEvents, true);
  const hint = deriveProgressHint(t, streamEvents, true);
  if (pres.headline && hint && pres.headline.trim() === hint.trim()) {
    return t("chat.run.progressWorking");
  }
  if (hint) return hint;
  if (!pres.headline) return t("chat.run.progressWorking");
  return "";
}

/**
 * Group SSE events by specialist_selected boundaries for compact run UI.
 *
 * @param {unknown[]} events
 * @returns {Array<{ key: string, from: string, to: string, isOrphan: boolean, events: unknown[] }>}
 */
export function buildSpecialistStreamGroups(events) {
  if (!Array.isArray(events) || events.length === 0) return [];
  /** @type {Array<{ key: string, from: string, to: string, isOrphan: boolean, events: unknown[] }>} */
  const groups = [];
  /** @type {{ key: string, from: string, to: string, isOrphan: boolean, events: unknown[] } | null} */
  let current = null;
  /** @type {unknown[]} */
  let orphan = [];

  const flushOrphan = () => {
    if (orphan.length === 0) return;
    groups.push({
      key: `orphan-${groups.length}`,
      from: "",
      to: "",
      isOrphan: true,
      events: [...orphan],
    });
    orphan = [];
  };

  for (const ev of events) {
    if (!ev || typeof ev !== "object") continue;
    if (isHiddenFromSpecialistRunTrace(ev)) continue;
    const type = String(ev.type || "");
    if (type === "specialist_selected") {
      flushOrphan();
      const fr = String(ev.from || "");
      const to = String(ev.to || "");
      current = {
        key: `${fr}→${to}-${groups.length}`,
        from: fr,
        to,
        isOrphan: false,
        events: [ev],
      };
      groups.push(current);
      continue;
    }
    if (current) {
      current.events.push(ev);
    } else {
      orphan.push(ev);
    }
  }
  flushOrphan();
  return groups.filter((g) => g.events.length > 0);
}

/**
 * Hide specialist rail when the stream is only low-signal preamble (no routing yet).
 *
 * @param {unknown[]} streamEvents
 * @returns {boolean}
 */
export function shouldShowSubagentRail(streamEvents) {
  const groups = buildSpecialistStreamGroups(streamEvents);
  if (groups.length === 0) return false;
  if (groups.length === 1) {
    const g = groups[0];
    if (g.isOrphan && g.events.length <= 2) return false;
  }
  return true;
}

function normalizedHasDegraded(normalized) {
  if (!normalized || typeof normalized !== "object") return false;
  const rt = normalized.retrieval_trace;
  const gc = normalized.graph_context;
  const rtDeg = rt && typeof rt === "object" && Array.isArray(rt.degraded) && rt.degraded.length > 0;
  const gcDeg = gc && typeof gc === "object" && Array.isArray(gc.degraded) && gc.degraded.length > 0;
  return Boolean(rtDeg || gcDeg);
}

function streamHasErrorEvent(streamEvents) {
  if (!Array.isArray(streamEvents)) return false;
  return streamEvents.some((e) => e && typeof e === "object" && String(e.type || "") === "error");
}

/**
 * @param {{
 *   normalized: Record<string, unknown> | null | undefined,
 *   isRunActive: boolean,
 *   streamEvents?: unknown[],
 * }} input
 * @returns {{
 *   runState: 'running' | 'done' | 'warning' | 'degraded' | 'failed',
 *   streamWarningCount: number,
 * }}
 */
export function deriveRunState({ normalized, isRunActive, streamEvents = [] }) {
  const warnings = normalized && Array.isArray(normalized.warnings) ? normalized.warnings : [];
  const streamWarnings = Array.isArray(streamEvents)
    ? streamEvents.filter((e) => e && typeof e === "object" && e.type === "warning").length
    : 0;
  if (isRunActive) return { runState: "running", streamWarningCount: streamWarnings };
  if (streamHasErrorEvent(streamEvents)) return { runState: "failed", streamWarningCount: streamWarnings };
  if (warnings.length > 0 || streamWarnings > 0) return { runState: "warning", streamWarningCount: streamWarnings };
  if (normalizedHasDegraded(normalized)) return { runState: "degraded", streamWarningCount: streamWarnings };
  return { runState: "done", streamWarningCount: streamWarnings };
}

/**
 * @param {{
 *   normalized: Record<string, unknown>,
 *   streamEvents?: unknown[],
 *   agentToolTrace?: unknown[],
 *   retrievalMode?: string,
 * }} input
 * @returns {boolean}
 */
export function shouldOfferRunInspector({ normalized, streamEvents = [], agentToolTrace = [], retrievalMode }) {
  if (retrievalMode !== "agent") return false;
  if (!normalized || typeof normalized !== "object") return false;
  const hasTrace = Array.isArray(agentToolTrace) && agentToolTrace.length > 0;
  const hasEvents = Array.isArray(streamEvents) && streamEvents.length > 0;
  const gc = normalized.graph_context;
  const rt = normalized.retrieval_trace;
  const graphRich = Boolean(
    gc &&
      typeof gc === "object" &&
      ((Array.isArray(gc.methods) && gc.methods.length > 0) ||
        (Array.isArray(gc.datasets) && gc.datasets.length > 0) ||
        (Array.isArray(gc.degraded) && gc.degraded.length > 0) ||
        Boolean(gc.error)),
  );
  const rtRich = Boolean(
    rt &&
      typeof rt === "object" &&
      (Number(rt.hit_count) > 0 ||
        Number(rt.citations_returned) > 0 ||
        (Array.isArray(rt.degraded) && rt.degraded.length > 0) ||
        Boolean(rt.retrieval_policy)),
  );
  return Boolean(hasTrace || hasEvents || graphRich || rtRich);
}
