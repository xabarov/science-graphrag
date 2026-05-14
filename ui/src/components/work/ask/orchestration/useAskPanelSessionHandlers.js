import { useCallback } from "react";

import {
  createAskSession as createAskSessionRequest,
  deleteAskSession as deleteAskSessionRequest,
  formatResearchApiError,
  listAskSessions as listAskSessionsRequest,
  patchAskSession as patchAskSessionRequest,
} from "../../../../services/researchApi.js";
import {
  apiSessionsToBundle,
  entriesToApiTurns,
  isServerAskSessionId,
} from "../session/askSessionServerBridge.js";
import {
  createAskSession,
  getActiveSessionEntries,
  getAskSessionEntries,
  readAskSessionUi,
  removeAskSession,
  removeAskSessionTurn,
  replaceScopeBundle,
  setActiveAskSession,
  truncateAskSessionFromTurn,
} from "../session/askSessionState.js";

/**
 * Session / thread mutation handlers for Ask panel (local + optional server sync).
 *
 * @param {{
 *   abort: () => void,
 *   bumpSessions: () => void,
 *   scopeKeyRef: { current: string },
 *   serverSync: boolean,
 *   setHistory: (entries: unknown[]) => void,
 *   setQuery: (q: string) => void,
 *   setWorkId: (id: string) => void,
 *   setNormalized: (v: unknown) => void,
 *   setError: (v: unknown) => void,
 *   onUrlSessionIdChange?: (sessionId: string) => void,
 *   activeSessionId: string | null,
 *   isLoading: boolean,
 *   performAgentSubmit: (
 *     q: string,
 *     opts?: { workIdForTurn?: string, userStructuredAnswer?: { request_id: string, answers: unknown[] } },
 *   ) => Promise<void>,
 * }} args
 */
export function useAskPanelSessionHandlers({
  abort,
  bumpSessions,
  scopeKeyRef,
  serverSync,
  setHistory,
  setQuery,
  setWorkId,
  setNormalized,
  setError,
  onUrlSessionIdChange,
  activeSessionId,
  isLoading,
  performAgentSubmit,
}) {
  const onRestartFromTurn = useCallback(
    async (turnId) => {
      if (isLoading) abort();
      const sk = scopeKeyRef.current;
      const sid = String(activeSessionId || "").trim();
      const tid = String(turnId || "").trim();
      if (!sid || !tid) return;
      const before = getAskSessionEntries(sk, sid);
      const entry = before.find((e) => e.id === tid);
      if (!entry || !String(entry.query || "").trim()) return;
      truncateAskSessionFromTurn(sk, sid, tid);
      bumpSessions();
      setHistory(getAskSessionEntries(sk, sid));
      if (serverSync && isServerAskSessionId(sid)) {
        try {
          await patchAskSessionRequest(sk, sid, {
            turns: entriesToApiTurns(getAskSessionEntries(sk, sid)),
            active: true,
          });
        } catch {
          /* non-fatal */
        }
      }
      setWorkId(String(entry.workId || "").trim());
      setQuery(String(entry.query || "").trim());
      await performAgentSubmit(String(entry.query || "").trim(), { workIdForTurn: entry.workId });
    },
    [abort, activeSessionId, bumpSessions, isLoading, performAgentSubmit, serverSync, scopeKeyRef, setHistory, setQuery, setWorkId],
  );

  const onClearChat = useCallback(async () => {
    abort();
    const sk = scopeKeyRef.current;
    const oldId = String(readAskSessionUi(sk).activeId || "");
    try {
      if (serverSync) {
        if (oldId && isServerAskSessionId(oldId)) {
          try {
            await deleteAskSessionRequest(sk, oldId);
          } catch {
            /* non-fatal: session may only exist locally */
          }
        }
        await createAskSessionRequest(sk, {});
        const res = await listAskSessionsRequest(sk);
        replaceScopeBundle(sk, apiSessionsToBundle(res.data));
        bumpSessions();
        const aid = res.data?.active_session_id;
        if (aid) onUrlSessionIdChange?.(String(aid));
      } else {
        createAskSession(sk);
        bumpSessions();
        const afterId = String(readAskSessionUi(sk).activeId || "");
        if (oldId && oldId !== afterId) removeAskSession(sk, oldId);
        bumpSessions();
        const next = String(readAskSessionUi(sk).activeId || "");
        if (next) onUrlSessionIdChange?.(next);
      }
      setHistory(getActiveSessionEntries(scopeKeyRef.current));
      setQuery("");
      setNormalized(null);
      setError(null);
    } catch (err) {
      setError(formatResearchApiError(err));
    }
  }, [abort, bumpSessions, onUrlSessionIdChange, serverSync, scopeKeyRef, setHistory, setQuery, setNormalized, setError]);

  const onDeleteSession = useCallback(
    async (sessionId) => {
      abort();
      const sk = scopeKeyRef.current;
      const sid = String(sessionId || "").trim();
      if (!sid) return;
      try {
        if (serverSync && isServerAskSessionId(sid)) {
          await deleteAskSessionRequest(sk, sid);
          const res = await listAskSessionsRequest(sk);
          replaceScopeBundle(sk, apiSessionsToBundle(res.data));
          bumpSessions();
          const aid = res.data?.active_session_id;
          if (aid) onUrlSessionIdChange?.(String(aid));
        } else {
          const { nextActiveId } = removeAskSession(sk, sid);
          bumpSessions();
          if (nextActiveId) onUrlSessionIdChange?.(String(nextActiveId));
        }
        setHistory(getActiveSessionEntries(scopeKeyRef.current));
        setQuery("");
        setNormalized(null);
      } catch (err) {
        setError(formatResearchApiError(err));
      }
    },
    [abort, bumpSessions, onUrlSessionIdChange, serverSync, scopeKeyRef, setHistory, setQuery, setNormalized, setError],
  );

  const onDeleteTurn = useCallback(
    async (turnId) => {
      if (isLoading) abort();
      const sk = scopeKeyRef.current;
      const sid = String(activeSessionId || "").trim();
      const tid = String(turnId || "").trim();
      if (!sid || !tid) return;
      const before = getAskSessionEntries(sk, sid);
      if (!before.some((e) => e.id === tid)) return;
      removeAskSessionTurn(sk, sid, tid);
      const after = getAskSessionEntries(sk, sid);
      bumpSessions();
      setHistory(after);
      if (serverSync && isServerAskSessionId(sid)) {
        try {
          await patchAskSessionRequest(sk, sid, {
            turns: entriesToApiTurns(after),
            active: true,
          });
        } catch {
          /* non-fatal */
        }
      }
    },
    [abort, activeSessionId, bumpSessions, isLoading, serverSync, scopeKeyRef, setHistory],
  );

  const onActiveSessionChange = useCallback(
    async (sessionId) => {
      const sk = scopeKeyRef.current;
      setActiveAskSession(sk, sessionId);
      bumpSessions();
      onUrlSessionIdChange?.(sessionId);
      if (serverSync && sessionId && isServerAskSessionId(sessionId)) {
        try {
          await patchAskSessionRequest(sk, sessionId, { active: true });
        } catch {
          /* non-fatal */
        }
      }
    },
    [bumpSessions, onUrlSessionIdChange, serverSync, scopeKeyRef],
  );

  const onNewSession = useCallback(async () => {
    const sk = scopeKeyRef.current;
    if (serverSync) {
      try {
        await createAskSessionRequest(sk, {});
        const res = await listAskSessionsRequest(sk);
        replaceScopeBundle(sk, apiSessionsToBundle(res.data));
        bumpSessions();
        const aid = res.data?.active_session_id;
        if (aid) onUrlSessionIdChange?.(String(aid));
      } catch (err) {
        setError(formatResearchApiError(err));
      }
      return;
    }
    const id = createAskSession(sk);
    bumpSessions();
    if (id) onUrlSessionIdChange?.(id);
  }, [serverSync, bumpSessions, onUrlSessionIdChange, scopeKeyRef, setError]);

  return {
    onRestartFromTurn,
    onClearChat,
    onDeleteSession,
    onDeleteTurn,
    onActiveSessionChange,
    onNewSession,
  };
}
