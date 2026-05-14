import {
  humanizeUnknownCode,
  mapAnswerClassToLabel,
  mapRouteReasonToLabel,
  mapSpecialistToLabel,
} from "../agentRunVocabulary.js";

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
