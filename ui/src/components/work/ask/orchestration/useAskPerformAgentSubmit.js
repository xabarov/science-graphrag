import { useCallback } from "react";

import { PDF_READ_USER_MESSAGE_TOKEN } from "../../../../services/research/pdfReadUi.js";
import { patchAskSession as patchAskSessionRequest } from "../../../../services/researchApi.js";
import { rememberAskHistory } from "../session/askHistoryState.js";
import {
  appendAskSessionTurn,
  appendAskSessionTurnToSession,
  buildAgentHistoryDigest,
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

/** Fixed retrieval depth for API compatibility (no UI control). */
const ASK_DEFAULT_TOP_K = 5;

/**
 * @param {{
 *   sk: string,
 *   submitSid: string,
 *   q: string,
 *   turn: ReturnType<typeof buildAskSessionTurnRecord>,
 *   serverSync: boolean,
 *   scopeKeyRef: { current: string },
 *   composerSuppressHydrateTurnIdRef: { current: string },
 *   setHistory: (entries: unknown[]) => void,
 *   setNormalized: (v: unknown) => void,
 *   bumpSessions: () => void,
 * }} ctx
 */
async function commitPersistedTurnToUiAndServer(ctx) {
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
      patchAskSessionRequest: patchAskSessionRequest,
    });
  }
  setNormalized(null);
  bumpSessions();
  await patchServerAskSessionTurnsIfSynced({
    serverSync,
    sk,
    submitSid,
    entriesAfter,
    patchAskSessionRequest: patchAskSessionRequest,
  });
}

/**
 * Agent submit + local/server turn persistence for Ask panel.
 *
 * @param {{
 *   submit: (args: object) => Promise<object>,
 *   webResearchEnabled: boolean,
 *   agentMode: "agent" | "plan",
 *   workId: string,
 *   activeSessionId: string | null,
 *   locked: boolean,
 *   inWorkspace: boolean,
 *   corpusWorkspaceOnly: boolean,
 *   bumpSessions: () => void,
 *   serverSync: boolean,
 *   t: (key: string) => string,
 *   scopeKeyRef: { current: string },
 *   streamFailureRef: { current: string },
 *   composerSuppressHydrateTurnIdRef: { current: string },
 *   setStreamingTarget: (v: unknown) => void,
 *   setPendingUserQuery: (q: string) => void,
 *   setQuery: (q: string) => void,
 *   setError: (e: unknown) => void,
 *   setNormalized: (v: unknown) => void,
 *   setHistory: (entries: unknown[]) => void,
 * }} args
 */
export function useAskPerformAgentSubmit({
  submit,
  webResearchEnabled,
  agentMode,
  workId,
  activeSessionId,
  locked,
  inWorkspace,
  corpusWorkspaceOnly,
  bumpSessions,
  serverSync,
  t,
  scopeKeyRef,
  streamFailureRef,
  composerSuppressHydrateTurnIdRef,
  setStreamingTarget,
  setPendingUserQuery,
  setQuery,
  setError,
  setNormalized,
  setHistory,
}) {
  return useCallback(
    async (queryText, { workIdForTurn, userStructuredAnswer, pdfReadRequest } = {}) => {
      const rawQ = String(queryText || "");
      const qTrim = rawQ.trim();
      const pdfUrl =
        pdfReadRequest && typeof pdfReadRequest === "object"
          ? String(pdfReadRequest.pdf_url || "").trim()
          : "";
      if (!qTrim && !pdfUrl) return null;
      const q = qTrim || PDF_READ_USER_MESSAGE_TOKEN;
      const turnWorkId = workIdForTurn != null ? String(workIdForTurn).trim() : String(workId || "").trim();
      const submitSk = scopeKeyRef.current;
      const submitSid = String(activeSessionId || "").trim();
      setStreamingTarget({ scopeKey: submitSk, sessionId: submitSid });
      setPendingUserQuery(q === PDF_READ_USER_MESSAGE_TOKEN ? t("askPanel.pdfRead.userTurnLabel") : q);
      setQuery("");
      try {
        const historyForDigest = submitSid ? getAskSessionEntries(submitSk, submitSid) : getActiveSessionEntries(submitSk);
        const historyDigest = buildAgentHistoryDigest(historyForDigest);
        let pack;
        try {
          pack = await submit({
            query: q,
            threadId: submitSid || null,
            historyDigest,
            userStructuredAnswer: userStructuredAnswer && typeof userStructuredAnswer === "object" ? userStructuredAnswer : null,
            pdfReadRequest: pdfReadRequest && typeof pdfReadRequest === "object" ? pdfReadRequest : null,
            webResearchEnabled,
            agentMode,
          });
        } catch (submitExc) {
          composerSuppressHydrateTurnIdRef.current = "";
          setQuery(q);
          throw submitExc;
        }
        const queryMode =
          locked || inWorkspace ? "workspace" : corpusWorkspaceOnly ? "workspace_corpus" : turnWorkId ? "scoped" : "global";
        const sk = submitSk;
        const persistedStreamEvents = Array.isArray(pack?.streamEvents) ? pack.streamEvents : [];
        const persistedToolTrace = Array.isArray(pack?.agentToolTrace) ? pack.agentToolTrace : [];

        if (!pack?.normalized) {
          const rawFail = String(streamFailureRef.current || "").trim();
          streamFailureRef.current = "";
          const failMsg = rawFail || t("askPanel.agentIncompleteTurn");
          setError(failMsg);
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
          await commitPersistedTurnToUiAndServer({
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
          });
          return {
            ok: false,
            streamEvents: persistedStreamEvents,
            agentToolTrace: persistedToolTrace,
          };
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
        await commitPersistedTurnToUiAndServer({
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
        });
        return { ok: true, normalized: nextNormalized, toolTrace: persistedToolTrace };
      } finally {
        setPendingUserQuery("");
        setStreamingTarget(null);
      }
    },
    [
      submit,
      webResearchEnabled,
      agentMode,
      workId,
      activeSessionId,
      locked,
      inWorkspace,
      corpusWorkspaceOnly,
      bumpSessions,
      serverSync,
      t,
      scopeKeyRef,
      streamFailureRef,
      composerSuppressHydrateTurnIdRef,
      setStreamingTarget,
      setPendingUserQuery,
      setQuery,
      setError,
      setNormalized,
      setHistory,
    ],
  );
}
