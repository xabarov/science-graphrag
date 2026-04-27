/**
 * Presentation-only helpers for agent chat run chrome (no transport changes).
 *
 * Live UX phases (rollout / fallback):
 * - Primary: `buildLiveStatusPresentation` headline + optional activity chips while streaming.
 * - Secondary: safe explanation lines (reason/summary only; no raw tool args).
 * - Fallback: if explanations are disabled or empty, inspector + recent lines still carry detail.
 */

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
  "product_step",
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
    if (MEANINGFUL_STREAM_TYPES.has(type)) return ev;
  }
  return null;
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
    return t("chat.stream.intent", { cls: String(event.answer_class || ""), src: String(event.source || "") });
  }
  if (type === "specialist_selected") {
    return t("chat.stream.route", { fr: String(event.from || ""), to: String(event.to || "") });
  }
  if (type === "tool_search_result") {
    const reason = String(event.reason || "");
    const skipNote = event.skipped ? ` ${t("chat.stream.shortlistSkipped")}` : "";
    return t("chat.stream.toolSearch", { spec: String(event.specialist || ""), reason: `${reason}${skipNote}` });
  }
  if (type === "evidence_ready") {
    return t("chat.stream.evidenceReady", { n: String(event.citation_count ?? "") });
  }
  if (type === "context_compacted") {
    const ex = String(event.session_summary_excerpt || "").slice(0, 160);
    return t("chat.stream.contextCompacted", { excerpt: ex });
  }
  if (type === "warning") {
    return t("chat.stream.warningLine", {
      code: String(event.code || ""),
      message: String(event.message || "").slice(0, 180),
    });
  }
  if (type === "subagent_started") {
    return t("chat.stream.subagentStarted", {
      id: String(event.subagent_id || event.name || ""),
    });
  }
  if (type === "subagent_progress") {
    const rawSummary = String(event.summary || event.tool || "");
    const tool = String(event.tool || "");
    const summary =
      tool && rawSummary === tool ? mapToolNameToUserLabel(t, tool) : rawSummary.slice(0, 120);
    return t("chat.stream.subagentProgress", {
      id: String(event.subagent_id || ""),
      summary,
    });
  }
  if (type === "subagent_finished") {
    return t("chat.stream.subagentFinished", {
      id: String(event.subagent_id || ""),
    });
  }
  if (type === "answer_synthesis_started") {
    return t("chat.stream.answerSynthesisStarted");
  }
  if (type === "answer_synthesis_finished") {
    return t("chat.stream.answerSynthesisFinished");
  }
  if (type === "product_step") {
    const code = String(event.code || "");
    if (code === "using_tool") {
      const tool = String(event.tool || "").trim() || "tool";
      return t("chat.run.productStep.using_tool", { tool: mapToolNameToUserLabel(t, tool) });
    }
    const key = `chat.run.productStep.${code}`;
    const out = t(key);
    return out === key ? code : out;
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
 * One formatted line per event (chronological), for expandable live status.
 *
 * @param {(key: string, vars?: Record<string, string>) => string} t
 * @param {unknown[]} events
 * @param {number} [limit]
 * @returns {string[]}
 */
export function collectFormattedStreamLines(t, events, limit = 24) {
  if (!Array.isArray(events) || events.length === 0) return [];
  const lines = [];
  for (const ev of events) {
    if (!ev || typeof ev !== "object") continue;
    const line = formatStreamEventOneLine(t, ev);
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
 * Safe, short "how it is working" lines (no raw args_summary, no debug_events).
 *
 * @param {(key: string, vars?: Record<string, string>) => string} t
 * @param {unknown[]} events
 * @param {number} [maxLines]
 * @returns {string[]}
 */
export function collectSafeExplanationLines(t, events, maxLines = 6) {
  if (!Array.isArray(events) || events.length === 0) return [];
  /** @type {string[]} */
  const raw = [];
  for (const ev of events) {
    if (!ev || typeof ev !== "object") continue;
    const type = String(ev.type || "");
    if (type === "specialist_selected") {
      const reason = String(ev.reason || "").trim();
      if (reason) {
        raw.push(t("chat.run.liveExplain.routeReason", { reason: reason.slice(0, 160) }));
      }
    } else if (type === "intent_classified") {
      const reason = String(ev.reason || "").trim();
      if (reason) {
        raw.push(
          t("chat.run.liveExplain.intentReason", {
            cls: String(ev.answer_class || ""),
            reason: reason.slice(0, 160),
          }),
        );
      }
    } else if (type === "subagent_started") {
      const summary = String(ev.summary || "").trim();
      if (summary) {
        raw.push(
          t("chat.run.liveExplain.subagentSummary", {
            id: String(ev.subagent_id || ""),
            summary: summary.slice(0, 160),
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
 *   activityChips: Array<{ tool: string, label: string }>,
 *   explanations: string[],
 *   recentLines: string[],
 *   showRecentToggle: boolean,
 *   showExplainToggle: boolean,
 * }} LiveStatusPresentation
 */

/**
 * Single source of truth for the live-run card (headline, chips, explanations, recent list).
 *
 * @param {(key: string, vars?: Record<string, string>) => string} t
 * @param {unknown[]} streamEvents
 * @param {boolean} isRunActive
 * @returns {LiveStatusPresentation}
 */
export function buildLiveStatusPresentation(t, streamEvents, isRunActive) {
  const list = Array.isArray(streamEvents) ? streamEvents : [];
  const meaningful = pickLastMeaningfulStreamEvent(list);
  let headline = meaningful ? formatStreamEventOneLine(t, meaningful) : "";
  if (!headline) {
    const tc = pickLastToolCallEvent(list);
    headline = tc ? formatStreamEventOneLine(t, tc) : "";
  }
  const toolNames = isRunActive ? collectRecentToolNamesForChips(list, 4) : [];
  let activityChips = toolNames.map((tool) => ({ tool, label: mapToolNameToUserLabel(t, tool) }));
  if (headline) {
    activityChips = activityChips.filter((chip) => chip.label.trim() !== headline.trim());
  }
  const explanations = isRunActive ? collectSafeExplanationLines(t, list, 6) : [];

  const allLines = collectFormattedStreamLines(t, list, 32);
  const recentLines = headline ? allLines.filter((line) => line !== headline) : allLines;

  const rawCount = list.filter((e) => e && typeof e === "object").length;
  const showRecentToggle = rawCount >= 2 && recentLines.length > 0;
  const showExplainToggle = explanations.length > 0;

  if (!isRunActive && !headline) {
    return {
      headline: "",
      activityChips: [],
      explanations: [],
      recentLines: [],
      showRecentToggle: false,
      showExplainToggle: false,
    };
  }

  return {
    headline,
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
