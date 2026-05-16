import { useEffect, useRef } from "react";

import {
  clearInflightRunSnapshot,
  readInflightRunSnapshot,
} from "../session/askRunPersistence.js";
import { readAskComposerDraft } from "../session/askComposerDraft.js";
import { sessionExistsInScope, setActiveAskSession } from "../session/askSessionState.js";
import { finalizeAgentStreamTurn } from "./askStreamTurnFinalize.js";

/**
 * On mount, restore in-flight agent run UI and resume SSE when user returns from another route.
 *
 * @param {{
 *   scopeKey: string,
 *   activeSessionId: string | null,
 *   onUrlSessionIdChange?: (sessionId: string) => void,
 *   workspaceId: string,
 *   locked: boolean,
 *   inWorkspace: boolean,
 *   corpusWorkspaceOnly: boolean,
 *   workId: string,
 *   serverSync: boolean,
 *   scopeKeyRef: { current: string },
 *   streamFailureRef: { current: string },
 *   composerSuppressHydrateTurnIdRef: { current: string },
 *   resumeStream: (args: { runId: string, afterSeq?: number }) => Promise<void>,
 *   streamEventsCaptureRef: { current: unknown[] },
 *   toolTraceCaptureRef: { current: unknown[] },
 *   lastStreamNormalizedRef: { current: unknown },
 *   setStreamEvents: (v: unknown[] | ((p: unknown[]) => unknown[])) => void,
 *   setAgentToolTrace: (v: unknown[]) => void,
 *   setPendingUserQuery: (q: string) => void,
 *   setStreamingTarget: (v: { scopeKey: string, sessionId: string } | null) => void,
 *   setQuery: (q: string) => void,
 *   setHistory: (entries: unknown[]) => void,
 *   setNormalized: (v: unknown) => void,
 *   setError: (v: unknown) => void,
 *   bumpSessions: () => void,
 *   setResumeUiStatus?: (status: string) => void,
 *   t: (key: string) => string,
 * }} args
 */
export function useAskInflightResume({
  scopeKey,
  activeSessionId,
  onUrlSessionIdChange,
  workspaceId,
  locked,
  inWorkspace,
  corpusWorkspaceOnly,
  workId,
  serverSync,
  scopeKeyRef,
  streamFailureRef,
  composerSuppressHydrateTurnIdRef,
  resumeStream,
  streamEventsCaptureRef,
  toolTraceCaptureRef,
  lastStreamNormalizedRef,
  setStreamEvents,
  setAgentToolTrace,
  setPendingUserQuery,
  setStreamingTarget,
  setQuery,
  setHistory,
  setNormalized,
  setError,
  bumpSessions,
  setResumeUiStatus,
  t,
}) {
  const attemptedRef = useRef(false);

  useEffect(() => {
    if (attemptedRef.current) return;
    const snap = readInflightRunSnapshot();
    if (!snap?.runId || snap.status !== "running" || String(snap.scopeKey || "") !== scopeKey) return;
    const sid = String(activeSessionId || "").trim();
    const snapSid = String(snap.sessionId || "").trim();
    if (!snapSid) {
      clearInflightRunSnapshot();
      return;
    }
    // Chat can open from shell without `ask_session` in URL (e.g. quick nav from Settings).
    // In that case, restore the run-owning session first, then resume stream on next effect turn.
    if (sid !== snapSid) {
      if (sessionExistsInScope(scopeKey, snapSid)) {
        setActiveAskSession(scopeKey, snapSid);
        onUrlSessionIdChange?.(snapSid);
        bumpSessions();
      }
      return;
    }
    attemptedRef.current = true;

    const draft = readAskComposerDraft(scopeKey, sid);
    if (draft) {
      setQuery(draft);
    }
    if (snap.pendingUserQuery) {
      setPendingUserQuery(snap.pendingUserQuery);
    }
    setStreamingTarget({ scopeKey: snap.scopeKey, sessionId: snapSid });
    if (Array.isArray(snap.streamEvents) && snap.streamEvents.length > 0) {
      setStreamEvents(snap.streamEvents);
      streamEventsCaptureRef.current = [...snap.streamEvents];
    }
    if (Array.isArray(snap.agentToolTrace) && snap.agentToolTrace.length > 0) {
      setAgentToolTrace(snap.agentToolTrace);
      toolTraceCaptureRef.current = [...snap.agentToolTrace];
    }

    const queryMode =
      locked || inWorkspace ? "workspace" : corpusWorkspaceOnly ? "workspace_corpus" : workId ? "scoped" : "global";
    const submitSk = snap.scopeKey;
    const submitSid = snap.sessionId;
    const q = snap.pendingUserQuery || "";
    const runId = String(snap.runId || "").trim();
    const hasServerRunId = runId.startsWith("run-");
    if (!hasServerRunId) {
      // Submit has started locally, but the server has not emitted run_started yet.
      // Keep the pending UI; the original stream will update the snapshot once run_id arrives.
      setResumeUiStatus?.("idle");
      return;
    }

    setResumeUiStatus?.("resuming");
    void (async () => {
      try {
        const pack = await resumeStream({ runId, afterSeq: snap.lastSeq || 0 });
        const resumeError = String(streamFailureRef.current || "").trim();
        if (!pack?.normalized && resumeError) {
          setError(resumeError);
          clearInflightRunSnapshot();
          return;
        }
        const mergedPack = pack || {
          normalized: lastStreamNormalizedRef.current,
          streamEvents: [...streamEventsCaptureRef.current],
          agentToolTrace: [...toolTraceCaptureRef.current],
        };
        if (!mergedPack.normalized) {
          // No terminal answer yet. Keep the pending UI and snapshot so the next mount/reconnect
          // can resume again instead of committing a synthetic failed turn.
          return;
        }
        await finalizeAgentStreamTurn({
          pack: mergedPack,
          queryText: q,
          turnWorkId: String(snap.workId || workId || "").trim(),
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
      } catch (err) {
        setError(String(err?.message || err || ""));
        clearInflightRunSnapshot();
      } finally {
        if (lastStreamNormalizedRef.current) {
          setPendingUserQuery("");
          setStreamingTarget(null);
        }
        setResumeUiStatus?.("idle");
      }
    })();
  }, [
    scopeKey,
    activeSessionId,
    onUrlSessionIdChange,
    workspaceId,
    locked,
    inWorkspace,
    corpusWorkspaceOnly,
    workId,
    serverSync,
    scopeKeyRef,
    streamFailureRef,
    composerSuppressHydrateTurnIdRef,
    resumeStream,
    streamEventsCaptureRef,
    toolTraceCaptureRef,
    lastStreamNormalizedRef,
    setStreamEvents,
    setAgentToolTrace,
    setPendingUserQuery,
    setStreamingTarget,
    setQuery,
    setHistory,
    setNormalized,
    setError,
    bumpSessions,
    setResumeUiStatus,
    t,
  ]);
}
