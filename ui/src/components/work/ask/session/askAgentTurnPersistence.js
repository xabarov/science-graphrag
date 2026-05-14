import { normalizeQueryResponse } from "../../../../services/researchApi.js";
import { entriesToApiTurns, isServerAskSessionId } from "./askSessionServerBridge.js";
import { readAskSessionUi } from "./askSessionState.js";
import { extractOpenStructuredQuestion } from "./askStreamArtifacts.js";

/** Max stream events persisted on a turn (matches prior inline slice(-80)). */
export const ASK_TURN_STREAM_EVENTS_CAP = 80;

/**
 * Build the `details` object stored on a session turn from a normalized agent payload.
 *
 * @param {Record<string, unknown>} normalized
 * @param {unknown[]} streamEvents
 * @param {unknown[]} agentToolTrace
 * @returns {Record<string, unknown>}
 */
export function buildAskTurnDetailsFromNormalized(normalized, streamEvents, agentToolTrace) {
  const persistedStreamEvents = Array.isArray(streamEvents) ? streamEvents : [];
  const persistedToolTrace = Array.isArray(agentToolTrace) ? agentToolTrace : [];
  return {
    answer: normalized.answer,
    citations: normalized.citations,
    graph_context: normalized.graph_context,
    retrieval_trace: normalized.retrieval_trace,
    answer_class: normalized.answer_class,
    evidence_summary: normalized.evidence_summary,
    warnings: normalized.warnings,
    inventory: normalized.inventory,
    relation_trace: normalized.relation_trace,
    quote_candidates: normalized.quote_candidates,
    idea_suggestions: normalized.idea_suggestions,
    bibliography: normalized.bibliography,
    thread_id: normalized.thread_id ?? null,
    duration_ms: normalized.duration_ms ?? null,
    phoenix_trace_id: normalized.phoenix_trace_id ?? null,
    session_summary_excerpt: normalized.session_summary_excerpt ?? null,
    run_metadata: normalized.run_metadata ?? null,
    product_path: normalized.product_path ?? null,
    product_markers: Array.isArray(normalized.product_markers) ? normalized.product_markers : [],
    stream_events: persistedStreamEvents.slice(-ASK_TURN_STREAM_EVENTS_CAP),
    agent_tool_trace: persistedToolTrace,
    open_structured_question: extractOpenStructuredQuestion(persistedStreamEvents),
  };
}

/**
 * Normalized payload used when the agent stream ends without a usable `normalized` object.
 *
 * @param {string} failMsg
 */
export function buildAskFailureNormalizedStub(failMsg) {
  return normalizeQueryResponse({
    answer: failMsg,
    citations: [],
    graph_context: {},
    retrieval_trace: {},
    warnings: [],
  });
}

/**
 * @param {{
 *   query: string,
 *   turnWorkId: string,
 *   topK: number,
 *   queryMode: string,
 *   answerText: string,
 *   citationCount: number,
 *   details: Record<string, unknown>,
 * }} args
 */
export function buildAskSessionTurnRecord({ query, turnWorkId, topK, queryMode, answerText, citationCount, details }) {
  return {
    query,
    workId: turnWorkId,
    topK,
    answer: answerText,
    citationCount,
    mode: queryMode,
    details,
  };
}

/**
 * Append turn to local session storage and return post-append state for UI + server patch.
 *
 * @param {{
 *   sk: string,
 *   submitSid: string,
 *   turn: ReturnType<typeof buildAskSessionTurnRecord>,
 *   rememberAskHistory: (turn: unknown) => void,
 *   appendAskSessionTurn: (sk: string, entry: unknown) => void,
 *   appendAskSessionTurnToSession: (sk: string, sid: string, entry: unknown) => void,
 *   readAskSessionUi: (sk: string, epoch?: unknown) => { activeId: string | null },
 *   getAskSessionEntries: (sk: string, sid: string) => unknown[],
 *   getActiveSessionEntries: (sk: string) => unknown[],
 *   scopeKeyRef: { current: string },
 * }} args
 * @returns {{ viewingThisRun: boolean, entriesAfter: unknown[], composerTurnId: string }}
 */
export function persistAskAgentTurnLocal({
  sk,
  submitSid,
  turn,
  rememberAskHistory,
  appendAskSessionTurn,
  appendAskSessionTurnToSession,
  readAskSessionUi,
  getAskSessionEntries,
  getActiveSessionEntries,
  scopeKeyRef,
}) {
  rememberAskHistory(turn);
  if (submitSid) {
    appendAskSessionTurnToSession(sk, submitSid, turn);
  } else {
    appendAskSessionTurn(sk, turn);
  }
  const currentSk = scopeKeyRef.current;
  const { activeId: currentActive } = readAskSessionUi(currentSk);
  const viewingThisRun = currentSk === sk && String(currentActive || "") === submitSid;
  const entriesAfter = submitSid ? getAskSessionEntries(sk, submitSid) : getActiveSessionEntries(sk);
  const composerTurnId = String(entriesAfter[0]?.id || "");
  return { viewingThisRun, entriesAfter, composerTurnId };
}

/**
 * Auto-title first user turn in a named session (local only).
 *
 * @param {{ sk: string, submitSid: string, q: string, entriesAfterLength: number, renameAskSession: (sk: string, sid: string, title: string) => void }} args
 * @returns {string | null} title applied, or null
 */
export function maybeRenameFirstAskSessionTurn({ sk, submitSid, q, entriesAfterLength, renameAskSession }) {
  if (!submitSid || entriesAfterLength !== 1 || !q) return null;
  const autoTitle = q.slice(0, 56) + (q.length > 56 ? "…" : "");
  renameAskSession(sk, submitSid, autoTitle);
  return autoTitle;
}

/**
 * @param {{
 *   serverSync: boolean,
 *   sk: string,
 *   submitSid: string,
 *   autoTitle: string,
 *   viewingThisRun: boolean,
 *   patchAskSessionRequest: (sk: string, sid: string, body: Record<string, unknown>) => Promise<unknown>,
 * }} args
 */
export async function patchServerAskSessionTitleIfSynced({
  serverSync,
  sk,
  submitSid,
  autoTitle,
  viewingThisRun,
  patchAskSessionRequest,
}) {
  if (!serverSync || !submitSid || !isServerAskSessionId(submitSid)) return;
  try {
    await patchAskSessionRequest(sk, submitSid, { title: autoTitle, active: viewingThisRun });
  } catch {
    /* non-fatal */
  }
}

/**
 * @param {{
 *   serverSync: boolean,
 *   sk: string,
 *   submitSid: string,
 *   entriesAfter: unknown[],
 *   patchAskSessionRequest: (sk: string, sid: string, body: Record<string, unknown>) => Promise<unknown>,
 * }} args
 */
export async function patchServerAskSessionTurnsIfSynced({ serverSync, sk, submitSid, entriesAfter, patchAskSessionRequest }) {
  if (!serverSync || !submitSid || !isServerAskSessionId(submitSid)) return;
  const activeNow = String(readAskSessionUi(sk).activeId || "");
  try {
    await patchAskSessionRequest(sk, submitSid, {
      turns: entriesToApiTurns(entriesAfter),
      active: activeNow === submitSid,
    });
  } catch {
    /* non-fatal */
  }
}
