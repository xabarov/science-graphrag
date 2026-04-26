/**
 * Presentation-only helpers for agent chat run chrome (no transport changes).
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
    if (MEANINGFUL_STREAM_TYPES.has(type)) return ev;
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
    const q = event.args_summary && typeof event.args_summary === "object" && event.args_summary.query != null
      ? String(event.args_summary.query).slice(0, 48)
      : "";
    return q ? t("chat.run.live.toolCallQuery", { tool, q: `"${q}${q.length >= 48 ? "…" : ""}"` }) : t("chat.run.live.toolCall", { tool });
  }
  if (type === "tool_result") {
    const err = event.error ? String(event.error) : "";
    const parts = [
      `${t("chat.stream.toolResultLabel")}: ${String(event.tool || "")}`,
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
    return t("chat.stream.subagentProgress", {
      id: String(event.subagent_id || ""),
      summary: String(event.summary || event.tool || "").slice(0, 120),
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
  return "";
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
  const streamWarnings = Array.isArray(streamEvents) ? streamEvents.filter((e) => e && typeof e === "object" && e.type === "warning").length : 0;
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
