import { useCallback } from "react";

import { PDF_READ_USER_MESSAGE_TOKEN } from "../../../../services/research/pdfReadUi.js";
import { ensureActiveAskSessionId, getAskSessionEntries, getActiveSessionEntries } from "../session/askSessionState.js";
import { buildAgentHistoryDigest } from "../session/askSessionState.js";
import { writeInflightRunSnapshot } from "../session/askRunPersistence.js";
import { writeAskComposerDraft } from "../session/askComposerDraft.js";
import { finalizeAgentStreamTurn } from "./askStreamTurnFinalize.js";

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
 *   workspaceId: string,
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
 *   onUrlSessionIdChange?: (sessionId: string) => void,
 *   inflightRunIdRef: { current: string },
 *   inflightLastSeqRef: { current: number },
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
  workspaceId,
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
  onUrlSessionIdChange,
  inflightRunIdRef,
  inflightLastSeqRef,
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
      const submitSid = String(activeSessionId || "").trim() || ensureActiveAskSessionId(submitSk);
      if (submitSid && submitSid !== String(activeSessionId || "").trim()) {
        onUrlSessionIdChange?.(submitSid);
        bumpSessions();
      }
      setStreamingTarget({ scopeKey: submitSk, sessionId: submitSid });
      const pendingLabel = q === PDF_READ_USER_MESSAGE_TOKEN ? t("askPanel.pdfRead.userTurnLabel") : q;
      setPendingUserQuery(pendingLabel);
      writeAskComposerDraft(submitSk, submitSid, "");
      setQuery("");
      writeInflightRunSnapshot({
        runId: inflightRunIdRef.current || `pending-${submitSid}`,
        scopeKey: submitSk,
        sessionId: submitSid,
        workspaceId: String(workspaceId || "").trim(),
        pendingUserQuery: pendingLabel,
        lastSeq: 0,
        streamEvents: [],
        agentToolTrace: [],
        status: "running",
        workId: turnWorkId,
      });
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
          writeInflightRunSnapshot(null);
          throw submitExc;
        }
        const queryMode =
          locked || inWorkspace ? "workspace" : corpusWorkspaceOnly ? "workspace_corpus" : turnWorkId ? "scoped" : "global";

        return finalizeAgentStreamTurn({
          pack,
          queryText: q,
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
        });
      } finally {
        setPendingUserQuery("");
        setStreamingTarget(null);
        inflightRunIdRef.current = "";
        inflightLastSeqRef.current = 0;
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
      workspaceId,
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
      onUrlSessionIdChange,
      inflightRunIdRef,
      inflightLastSeqRef,
    ],
  );
}
