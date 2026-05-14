import {
  humanizeUnknownCode,
  isRedundantIntentSource,
  mapAnswerClassToLabel,
  mapErrorCodeToLabel,
  mapIntentSourceToLabel,
  mapRouteReasonToLabel,
  mapSpecialistToLabel,
  mapToolSearchReasonToLabel,
} from "../agentRunVocabulary.js";

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
    const provenance =
      event.merge_provenance && typeof event.merge_provenance === "object"
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
