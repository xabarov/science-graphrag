import { useEffect } from "react";

import {
  formatResearchApiError,
  listAskSessions as listAskSessionsRequest,
} from "../../../../services/researchApi.js";
import { apiSessionsToBundle } from "../session/askSessionServerBridge.js";
import {
  getActiveSessionEntries,
  maybeMigrateStandaloneBundleToWorkspaceScope,
  migrateLegacyAskHistoryToSessions,
  readAskSessionUi,
  replaceScopeBundle,
  sessionExistsInScope,
  setActiveAskSession,
} from "../session/askSessionState.js";

/**
 * URL/session scope sync, server session list pull, and thread history hydration.
 *
 * @param {{
 *   scopeKey: string,
 *   locked: boolean,
 *   scopedWorkId: string | null,
 *   workspaceId: string,
 *   initialWorkId: string,
 *   urlSessionId: string,
 *   onUrlSessionIdChange?: (sessionId: string) => void,
 *   serverSync: boolean,
 *   sessionTick: number,
 *   bumpSessions: () => void,
 *   activeSessionId: string | null,
 *   setError: (v: unknown) => void,
 *   setHistory: (entries: unknown[]) => void,
 *   setQuery: (q: string) => void,
 *   composerSuppressHydrateTurnIdRef: { current: string },
 * }} args
 */
export function useAskSessionLifecycle({
  scopeKey,
  locked,
  scopedWorkId,
  workspaceId,
  initialWorkId,
  urlSessionId,
  onUrlSessionIdChange,
  serverSync,
  sessionTick,
  bumpSessions,
  activeSessionId,
  setError,
  setHistory,
  setQuery,
  composerSuppressHydrateTurnIdRef,
}) {
  useEffect(() => {
    const id = String(urlSessionId || "").trim();
    if (!id || !sessionExistsInScope(scopeKey, id)) return;
    const { activeId } = readAskSessionUi(scopeKey, sessionTick);
    if (activeId !== id) {
      setActiveAskSession(scopeKey, id);
      // eslint-disable-next-line react-hooks/set-state-in-effect
      bumpSessions();
    }
  }, [urlSessionId, scopeKey, bumpSessions, sessionTick]);

  useEffect(() => {
    const id = String(urlSessionId || "").trim();
    if (!activeSessionId || id === activeSessionId) return;
    if (id && sessionExistsInScope(scopeKey, id)) return;
    onUrlSessionIdChange?.(activeSessionId);
  }, [urlSessionId, activeSessionId, scopeKey, onUrlSessionIdChange]);

  useEffect(() => {
    if (!locked) {
      const ws = String(workspaceId || "").trim();
      if (ws) maybeMigrateStandaloneBundleToWorkspaceScope(ws);
    }
    migrateLegacyAskHistoryToSessions(scopeKey, (item) =>
      locked ? String(item.workId || "").trim() === String(scopedWorkId || "").trim() : true,
    );
    getActiveSessionEntries(scopeKey);
    // eslint-disable-next-line react-hooks/set-state-in-effect
    bumpSessions();
  }, [scopeKey, locked, scopedWorkId, workspaceId, bumpSessions]);

  useEffect(() => {
    if (!serverSync) return undefined;
    let cancelled = false;
    (async () => {
      try {
        const res = await listAskSessionsRequest(scopeKey);
        if (cancelled) return;
        replaceScopeBundle(scopeKey, apiSessionsToBundle(res.data));
        bumpSessions();
      } catch (err) {
        if (!cancelled) setError(formatResearchApiError(err));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [serverSync, scopeKey, bumpSessions, setError]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setHistory(getActiveSessionEntries(scopeKey));
  }, [scopeKey, sessionTick, setHistory]);

  useEffect(() => {
    if (locked || initialWorkId) return;
    const recent = getActiveSessionEntries(scopeKey);
    if (!recent[0]) return;
    const headId = String(recent[0].id || "");
    if (headId && headId === composerSuppressHydrateTurnIdRef.current) {
      return;
    }
    composerSuppressHydrateTurnIdRef.current = "";
    // eslint-disable-next-line react-hooks/set-state-in-effect -- composer draft only; scope stays URL-driven
    setQuery(recent[0].query);
  }, [locked, initialWorkId, scopeKey, composerSuppressHydrateTurnIdRef, setQuery]);
}
