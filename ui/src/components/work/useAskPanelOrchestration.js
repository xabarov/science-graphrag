import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  createAskSession as createAskSessionRequest,
  formatResearchApiError,
  getWorkDetail,
  getWorks,
  listAskSessions as listAskSessionsRequest,
  normalizeQueryResponse,
  patchAskSession as patchAskSessionRequest,
} from "../../services/researchApi.js";
import { useI18n } from "../../i18n/useI18n.js";
import { persistWorkId } from "../../pages/WorkspacePage/utils/workContext.js";
import { CHAT_PATH } from "../../routes/paths.js";
import { getWorkspace } from "../../utils/workspaceStore.js";
import { apiSessionsToBundle, entriesToApiTurns, isServerAskSessionId, readAskServerSyncPref } from "./askSessionServerBridge.js";
import { rememberAskHistory } from "./askHistoryState.js";
import {
  appendAskSessionTurn,
  buildAgentHistoryDigest,
  createAskSession,
  deriveAskScopeKey,
  getActiveSessionEntries,
  migrateLegacyAskHistoryToSessions,
  maybeMigrateStandaloneBundleToWorkspaceScope,
  readAskSessionUi,
  renameAskSession,
  replaceScopeBundle,
  sessionExistsInScope,
  setActiveAskSession,
} from "./askSessionState.js";
import { buildStandaloneTracePath } from "./traceabilityState.js";
import { useAskSubmit } from "./useAskSubmit.js";
import { normalizeWorkListItem } from "./workListLabel.js";

/** Fixed retrieval depth for API compatibility (no UI control). */
const ASK_DEFAULT_TOP_K = 5;

/**
 * Ask panel state, session scope, effects, and submit/session handlers.
 *
 * @param {{
 *   scopedWorkId?: string | null,
 *   initialWorkId?: string,
 *   workspaceWorkId?: string | null,
 *   workspaceId?: string,
 *   urlSessionId?: string,
 *   onUrlSessionIdChange?: (sessionId: string) => void,
 * }} props
 */
export function useAskPanelOrchestration({
  scopedWorkId = null,
  initialWorkId = "",
  workspaceWorkId = null,
  workspaceId = "",
  urlSessionId = "",
  onUrlSessionIdChange,
}) {
  const { t } = useI18n();
  const locked = Boolean(scopedWorkId && String(scopedWorkId).trim());
  const [query, setQuery] = useState("");
  const [workId, setWorkId] = useState(locked ? String(scopedWorkId).trim() : initialWorkId);
  const [workDetailsForChip, setWorkDetailsForChip] = useState(null);
  const [workspaceSearchOptions, setWorkspaceSearchOptions] = useState([]);
  const [error, setError] = useState(null);
  const [normalized, setNormalized] = useState(null);
  const [history, setHistory] = useState([]);
  const [retrievalJsonOpen, setRetrievalJsonOpen] = useState(false);
  const [sessionTick, setSessionTick] = useState(0);
  const [serverSync] = useState(() => readAskServerSyncPref());
  const [agentToolTrace, setAgentToolTrace] = useState([]);
  const [streamEvents, setStreamEvents] = useState([]);
  const [answerClassHint, setAnswerClassHint] = useState("");
  const [pendingUserQuery, setPendingUserQuery] = useState("");
  const skipHydrateWorkRef = useRef(false);
  const streamFailureRef = useRef("");

  const scopeKey = useMemo(() => deriveAskScopeKey({ locked, scopedWorkId, workspaceId }), [locked, scopedWorkId, workspaceId]);
  /**
   * Invariant: after any `await` (agent stream, patch), never use `scopeKey` from the outer `useCallback`
   * closure for localStorage / API scope — it can lag behind `deriveAskScopeKey` when URL or
   * `activeWorkspaceId` resolves mid-flight. Read `scopeKeyRef.current` instead.
   */
  const scopeKeyRef = useRef(scopeKey);
  scopeKeyRef.current = scopeKey;
  const bumpSessions = useCallback(() => setSessionTick((v) => v + 1), []);
  const { activeId: activeSessionId, sessions: sessionList } = readAskSessionUi(scopeKey, sessionTick);
  const inWorkspace = Boolean(workspaceWorkId && String(workspaceWorkId).trim());
  const corpusWorkspaceOnly = Boolean(String(workspaceId || "").trim() && !String(workId || "").trim() && !locked);
  const standaloneMode = !inWorkspace && !locked && !corpusWorkspaceOnly;

  const starterPromptKeys = useMemo(() => {
    if (locked) {
      return ["chat.thread.prompts.scoped.1", "chat.thread.prompts.scoped.2", "chat.thread.prompts.scoped.3"];
    }
    if (inWorkspace) {
      return ["chat.thread.prompts.workspacePaper.1", "chat.thread.prompts.workspacePaper.2", "chat.thread.prompts.workspacePaper.3"];
    }
    if (corpusWorkspaceOnly) {
      return ["chat.thread.prompts.workspaceCorpus.1", "chat.thread.prompts.workspaceCorpus.2", "chat.thread.prompts.workspaceCorpus.3"];
    }
    return ["chat.thread.prompts.standalone.1", "chat.thread.prompts.standalone.2", "chat.thread.prompts.standalone.3"];
  }, [locked, inWorkspace, corpusWorkspaceOnly]);

  const searchWorks = useCallback(
    async (q) => {
      const needle = String(q || "").trim().toLowerCase();
      if (workspaceId) {
        if (!needle) return workspaceSearchOptions;
        return workspaceSearchOptions.filter((item) => {
          const row = normalizeWorkListItem(item);
          return [
            row.title,
            row.doi,
            row.arxiv_id,
            row.venue,
            row.work_id,
            row.year != null ? String(row.year) : "",
          ]
            .filter(Boolean)
            .some((part) => String(part).toLowerCase().includes(needle));
        });
      }
      const res = await getWorks({ q: (q || "").trim(), limit: 40, offset: 0 });
      return res.data?.items || [];
    },
    [workspaceId, workspaceSearchOptions],
  );

  const onArticlePicked = useCallback((item) => {
    const row = normalizeWorkListItem(item);
    if (!row.work_id) return;
    const rich = Boolean(row.title || row.doi || row.arxiv_id || row.venue);
    if (rich) {
      skipHydrateWorkRef.current = true;
      setWorkDetailsForChip(row);
    }
    setWorkId(row.work_id);
  }, []);

  const { submit, isLoading } = useAskSubmit({
    workspaceId,
    onStart: () => {
      streamFailureRef.current = "";
      setError(null);
      setNormalized(null);
      setRetrievalJsonOpen(false);
      setAgentToolTrace([]);
      setStreamEvents([]);
    },
    onResult: setNormalized,
    onToolTrace: setAgentToolTrace,
    onStreamEvent: (event) => {
      if (!event || typeof event !== "object") return;
      setStreamEvents((prev) => [...prev, event].slice(-80));
    },
    onError: (msg) => {
      streamFailureRef.current = String(msg ?? "").trim();
      setError(msg);
    },
  });

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
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setWorkId(locked ? String(scopedWorkId).trim() : initialWorkId || "");
  }, [locked, scopedWorkId, initialWorkId]);

  useEffect(() => {
    if (!locked) {
      const ws = String(workspaceId || "").trim();
      if (ws) maybeMigrateStandaloneBundleToWorkspaceScope(ws);
    }
    migrateLegacyAskHistoryToSessions(scopeKey, (item) => (locked ? String(item.workId || "").trim() === String(scopedWorkId || "").trim() : true));
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
  }, [serverSync, scopeKey, bumpSessions]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setHistory(getActiveSessionEntries(scopeKey));
  }, [scopeKey, sessionTick]);

  useEffect(() => {
    if (locked || initialWorkId) return;
    const recent = getActiveSessionEntries(scopeKey);
    if (!recent[0]) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setQuery(recent[0].query);
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setWorkId(recent[0].workId);
  }, [locked, initialWorkId, scopeKey]);

  useEffect(() => {
    if (!workspaceId || locked) {
      setWorkspaceSearchOptions([]);
      return undefined;
    }
    let cancelled = false;
    (async () => {
      try {
        const ws = await getWorkspace(workspaceId);
        if (cancelled) return;
        const ids = Array.isArray(ws?.work_ids) ? ws.work_ids.map((x) => String(x || "").trim()).filter(Boolean) : [];
        if (!ids.length) {
          setWorkspaceSearchOptions([]);
          return;
        }
        const details = await Promise.all(
          ids.map(async (wid) => {
            try {
              const res = await getWorkDetail(wid);
              return normalizeWorkListItem(res.data || {}, wid);
            } catch {
              return normalizeWorkListItem({ work_id: wid }, wid);
            }
          }),
        );
        if (!cancelled) setWorkspaceSearchOptions(details);
      } catch {
        if (!cancelled) setWorkspaceSearchOptions([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [workspaceId, locked]);

  useEffect(() => {
    const w = String(workId || "").trim();
    if (!w) {
      setWorkDetailsForChip(null);
      return undefined;
    }
    if (skipHydrateWorkRef.current) {
      skipHydrateWorkRef.current = false;
      return undefined;
    }
    let cancelled = false;
    const tid = setTimeout(() => {
      getWorkDetail(w)
        .then((res) => {
          if (!cancelled) setWorkDetailsForChip(normalizeWorkListItem(res.data || {}, w));
        })
        .catch(() => {
          if (!cancelled) setWorkDetailsForChip(normalizeWorkListItem({ work_id: w }, w));
        });
    }, 220);
    return () => {
      cancelled = true;
      clearTimeout(tid);
    };
  }, [workId]);

  useEffect(() => {
    if (!locked && workId.trim()) persistWorkId(workId);
  }, [locked, workId]);

  const onSubmit = useCallback(
    async (e) => {
      e.preventDefault();
      const q = String(query || "").trim();
      if (!q) return;
      setPendingUserQuery(q);
      try {
        const historyDigest = buildAgentHistoryDigest(history);
        const pack = await submit({
          query,
          threadId: activeSessionId || null,
          historyDigest,
          answerClassHint: String(answerClassHint || "").trim() || null,
        });
        const queryMode = locked || inWorkspace ? "workspace" : corpusWorkspaceOnly ? "workspace_corpus" : workId ? "scoped" : "global";
        if (!pack?.normalized) {
          const sk = scopeKeyRef.current;
          const rawFail = String(streamFailureRef.current || "").trim();
          streamFailureRef.current = "";
          const failMsg = rawFail || t("askPanel.agentIncompleteTurn");
          setError(failMsg);
          const nextNormalized = normalizeQueryResponse({
            answer: failMsg,
            citations: [],
            graph_context: {},
            retrieval_trace: {},
            warnings: [],
          });
          const persistedStreamEvents = [];
          const persistedToolTrace = [];
          const details = {
            answer: nextNormalized.answer,
            citations: nextNormalized.citations,
            graph_context: nextNormalized.graph_context,
            retrieval_trace: nextNormalized.retrieval_trace,
            answer_class: nextNormalized.answer_class,
            evidence_summary: nextNormalized.evidence_summary,
            warnings: nextNormalized.warnings,
            inventory: nextNormalized.inventory,
            relation_trace: nextNormalized.relation_trace,
            quote_candidates: nextNormalized.quote_candidates,
            idea_suggestions: nextNormalized.idea_suggestions,
            bibliography: nextNormalized.bibliography,
            thread_id: nextNormalized.thread_id ?? null,
            duration_ms: nextNormalized.duration_ms ?? null,
            phoenix_trace_id: nextNormalized.phoenix_trace_id ?? null,
            session_summary_excerpt: nextNormalized.session_summary_excerpt ?? null,
            run_metadata: nextNormalized.run_metadata ?? null,
            stream_events: persistedStreamEvents.slice(-80),
            agent_tool_trace: persistedToolTrace,
          };
          const turn = {
            query,
            workId,
            topK: ASK_DEFAULT_TOP_K,
            answer: failMsg,
            citationCount: 0,
            mode: queryMode,
            details,
          };
          rememberAskHistory(turn);
          appendAskSessionTurn(sk, turn);
          setHistory(getActiveSessionEntries(sk));
          const sid = readAskSessionUi(sk).activeId;
          const entriesAfter = getActiveSessionEntries(sk);
          if (sid && entriesAfter.length === 1 && q) {
            const autoTitle = q.slice(0, 56) + (q.length > 56 ? "…" : "");
            renameAskSession(sk, sid, autoTitle);
            if (serverSync && isServerAskSessionId(sid)) {
              try {
                await patchAskSessionRequest(sk, sid, { title: autoTitle, active: true });
              } catch {
                /* non-fatal */
              }
            }
          }
          setNormalized(null);
          setQuery("");
          bumpSessions();
          if (serverSync) {
            const { activeId: sid2 } = readAskSessionUi(sk);
            if (sid2 && isServerAskSessionId(sid2)) {
              try {
                await patchAskSessionRequest(sk, sid2, { turns: entriesToApiTurns(getActiveSessionEntries(sk)), active: true });
              } catch {
                /* non-fatal */
              }
            }
          }
          return;
        }
        const sk = scopeKeyRef.current;
        const nextNormalized = pack.normalized;
        const persistedStreamEvents = Array.isArray(pack.streamEvents) ? pack.streamEvents : [];
        const persistedToolTrace = Array.isArray(pack.agentToolTrace) ? pack.agentToolTrace : [];
        const details = {
          answer: nextNormalized.answer,
          citations: nextNormalized.citations,
          graph_context: nextNormalized.graph_context,
          retrieval_trace: nextNormalized.retrieval_trace,
          answer_class: nextNormalized.answer_class,
          evidence_summary: nextNormalized.evidence_summary,
          warnings: nextNormalized.warnings,
          inventory: nextNormalized.inventory,
          relation_trace: nextNormalized.relation_trace,
          quote_candidates: nextNormalized.quote_candidates,
          idea_suggestions: nextNormalized.idea_suggestions,
          bibliography: nextNormalized.bibliography,
          thread_id: nextNormalized.thread_id ?? null,
          duration_ms: nextNormalized.duration_ms ?? null,
          phoenix_trace_id: nextNormalized.phoenix_trace_id ?? null,
          session_summary_excerpt: nextNormalized.session_summary_excerpt ?? null,
          run_metadata: nextNormalized.run_metadata ?? null,
          stream_events: persistedStreamEvents.slice(-80),
          agent_tool_trace: persistedToolTrace,
        };
        const turn = {
          query,
          workId,
          topK: ASK_DEFAULT_TOP_K,
          answer: nextNormalized.answer,
          citationCount: nextNormalized.citations.length,
          mode: queryMode,
          details,
        };
        rememberAskHistory(turn);
        appendAskSessionTurn(sk, turn);
        setHistory(getActiveSessionEntries(sk));
        const sid = readAskSessionUi(sk).activeId;
        const entriesAfter = getActiveSessionEntries(sk);
        if (sid && entriesAfter.length === 1 && q) {
          const autoTitle = q.slice(0, 56) + (q.length > 56 ? "…" : "");
          renameAskSession(sk, sid, autoTitle);
          if (serverSync && isServerAskSessionId(sid)) {
            try {
              await patchAskSessionRequest(sk, sid, { title: autoTitle, active: true });
            } catch {
              /* non-fatal */
            }
          }
        }
        setNormalized(null);
        setQuery("");
        bumpSessions();
        if (!serverSync) return;
        const { activeId: sid2 } = readAskSessionUi(sk);
        if (sid2 && isServerAskSessionId(sid2)) {
          try {
            await patchAskSessionRequest(sk, sid2, { turns: entriesToApiTurns(getActiveSessionEntries(sk)), active: true });
          } catch {
            /* non-fatal */
          }
        }
      } finally {
        setPendingUserQuery("");
      }
    },
    [
      submit,
      query,
      history,
      activeSessionId,
      answerClassHint,
      locked,
      inWorkspace,
      corpusWorkspaceOnly,
      workId,
      bumpSessions,
      serverSync,
      t,
    ],
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
    [bumpSessions, onUrlSessionIdChange, serverSync],
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
  }, [serverSync, bumpSessions, onUrlSessionIdChange]);

  const standaloneChatPath = buildStandaloneTracePath(CHAT_PATH, workId);

  const scopeEyebrow = inWorkspace || locked
    ? t("askPanel.banner.workspaceScoped")
    : corpusWorkspaceOnly
      ? t("askPanel.banner.workspaceCorpusTitle")
      : t("askPanel.banner.standalone");

  const handleWorkIdChange = useCallback((next) => {
    setWorkId(next);
    if (!String(next || "").trim()) setWorkDetailsForChip(null);
  }, []);

  const streamingHint = useMemo(() => (isLoading ? t("askPanel.agentStreamingHint") : ""), [isLoading, t]);

  return {
    t,
    locked,
    scopedWorkId,
    workspaceId,
    workspaceWorkId,
    query,
    setQuery,
    workId,
    workDetailsForChip,
    error,
    normalized,
    history,
    retrievalJsonOpen,
    setRetrievalJsonOpen,
    sessionList,
    activeSessionId,
    agentToolTrace,
    streamEvents,
    answerClassHint,
    setAnswerClassHint,
    pendingUserQuery,
    inWorkspace,
    corpusWorkspaceOnly,
    standaloneMode,
    starterPromptKeys,
    isLoading,
    onSubmit,
    onActiveSessionChange,
    onNewSession,
    searchWorks,
    onArticlePicked,
    handleWorkIdChange,
    standaloneChatPath,
    scopeEyebrow,
    streamingHint,
  };
}
