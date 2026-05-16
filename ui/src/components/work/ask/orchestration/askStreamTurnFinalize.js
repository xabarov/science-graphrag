import { PDF_READ_USER_MESSAGE_TOKEN } from "../../../../services/research/pdfReadUi.js";
import { patchAskSession as patchAskSessionRequest } from "../../../../services/researchApi.js";
import { rememberAskHistory } from "../session/askHistoryState.js";
import {
  appendAskSessionTurn,
  appendAskSessionTurnToSession,
  getActiveSessionEntries,
  getAskSessionEntries,
  readAskSessionUi,
  renameAskSession,
} from "../session/askSessionState.js";
import {
  buildAskFailureNormalizedStub,
  buildAskSessionTurnRecord,
  buildAskTurnDetailsFromNormalized,
  maybeRenameFirstAskSessionTurn,
  patchServerAskSessionTitleIfSynced,
  patchServerAskSessionTurnsIfSynced,
  persistAskAgentTurnLocal,
} from "../session/askAgentTurnPersistence.js";
import { clearInflightRunSnapshot } from "../session/askRunPersistence.js";

const ASK_DEFAULT_TOP_K = 5;

/**
 * Persist a completed (or failed) agent stream pack into session storage + optional server sync.
 *
 * @param {{
 *   pack: { normalized?: unknown, streamEvents?: unknown[], agentToolTrace?: unknown[] } | null,
 *   queryText: string,
 *   turnWorkId: string,
 *   queryMode: string,
 *   submitSk: string,
 *   submitSid: string,
 *   serverSync: boolean,
 *   scopeKeyRef: { current: string },
 *   composerSuppressHydrateTurnIdRef: { current: string },
 *   setHistory: (entries: unknown[]) => void,
 *   setNormalized: (v: unknown) => void,
 *   bumpSessions: () => void,
 *   streamFailureRef: { current: string },
 *   t: (key: string) => string,
 *   setError?: (e: unknown) => void,
 * }} ctx
 * @returns {Promise<{ ok: boolean, normalized?: unknown }>}
 */
export async function finalizeAgentStreamTurn(ctx) {
  const {
    pack,
    queryText,
    turnWorkId,
    queryMode,
    submitSk,
    submitSid,
    serverSync,
    scopeKeyRef,
    composerSuppressHydrateTurnIdRef,
    setHistory,
    setNormalized,
    bumpSessions,
    streamFailureRef,
    t,
    setError,
  } = ctx;
  const q = String(queryText || "").trim() || PDF_READ_USER_MESSAGE_TOKEN;
  const persistedStreamEvents = Array.isArray(pack?.streamEvents) ? pack.streamEvents : [];
  const persistedToolTrace = Array.isArray(pack?.agentToolTrace) ? pack.agentToolTrace : [];

  if (!pack?.normalized) {
    const rawFail = String(streamFailureRef.current || "").trim();
    streamFailureRef.current = "";
    const failMsg = rawFail || t("askPanel.agentIncompleteTurn");
    setError?.(failMsg);
    const nextNormalized = buildAskFailureNormalizedStub(failMsg);
    const details = buildAskTurnDetailsFromNormalized(nextNormalized, persistedStreamEvents, persistedToolTrace);
    const turn = buildAskSessionTurnRecord({
      query: q,
      turnWorkId,
      topK: ASK_DEFAULT_TOP_K,
      queryMode,
      answerText: failMsg,
      citationCount: 0,
      details,
    });
    await commitTurn({
      sk: submitSk,
      submitSid,
      q,
      turn,
      serverSync,
      scopeKeyRef,
      composerSuppressHydrateTurnIdRef,
      setHistory,
      setNormalized,
      bumpSessions,
    });
    clearInflightRunSnapshot();
    return { ok: false, streamEvents: persistedStreamEvents, agentToolTrace: persistedToolTrace };
  }

  const nextNormalized = pack.normalized;
  const details = buildAskTurnDetailsFromNormalized(nextNormalized, persistedStreamEvents, persistedToolTrace);
  const turn = buildAskSessionTurnRecord({
    query: q,
    turnWorkId,
    topK: ASK_DEFAULT_TOP_K,
    queryMode,
    answerText: nextNormalized.answer,
    citationCount: nextNormalized.citations.length,
    details,
  });
  await commitTurn({
    sk: submitSk,
    submitSid,
    q,
    turn,
    serverSync,
    scopeKeyRef,
    composerSuppressHydrateTurnIdRef,
    setHistory,
    setNormalized,
    bumpSessions,
  });
  clearInflightRunSnapshot();
  return { ok: true, normalized: nextNormalized, toolTrace: persistedToolTrace };
}

async function commitTurn(ctx) {
  const {
    sk,
    submitSid,
    q,
    turn,
    serverSync,
    scopeKeyRef,
    composerSuppressHydrateTurnIdRef,
    setHistory,
    setNormalized,
    bumpSessions,
  } = ctx;
  const { viewingThisRun, entriesAfter, composerTurnId } = persistAskAgentTurnLocal({
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
  });
  if (viewingThisRun) {
    setHistory(submitSid ? getAskSessionEntries(sk, submitSid) : getActiveSessionEntries(sk));
  }
  composerSuppressHydrateTurnIdRef.current = composerTurnId;
  const autoTitle = maybeRenameFirstAskSessionTurn({
    sk,
    submitSid,
    q,
    entriesAfterLength: entriesAfter.length,
    renameAskSession,
  });
  if (autoTitle != null) {
    await patchServerAskSessionTitleIfSynced({
      serverSync,
      sk,
      submitSid,
      autoTitle,
      viewingThisRun,
      patchAskSessionRequest,
    });
  }
  setNormalized(null);
  bumpSessions();
  await patchServerAskSessionTurnsIfSynced({
    serverSync,
    sk,
    submitSid,
    entriesAfter,
    patchAskSessionRequest,
  });
}
