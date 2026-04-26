import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import {
  createAskSession as createAskSessionRequest,
  formatResearchApiError,
  getWorkDetail,
  getWorks,
  listAskSessions as listAskSessionsRequest,
  normalizeQueryResponse,
  patchAskSession as patchAskSessionRequest,
} from "../../services/researchApi.js";
import { apiSessionsToBundle, entriesToApiTurns, isServerAskSessionId, readAskServerSyncPref } from "./askSessionServerBridge.js";
import { rememberAskHistory } from "./askHistoryState.js";
import {
  appendAskSessionTurn,
  buildAgentHistoryDigest,
  createAskSession,
  deriveAskScopeKey,
  getActiveSessionEntries,
  migrateLegacyAskHistoryToSessions,
  readAskSessionUi,
  renameAskSession,
  replaceScopeBundle,
  sessionExistsInScope,
  setActiveAskSession,
} from "./askSessionState.js";
import { buildStandaloneTracePath } from "./traceabilityState.js";
import { persistWorkId } from "../../pages/WorkspacePage/utils/workContext.js";
import { CHAT_PATH } from "../../routes/paths.js";
import { useI18n } from "../../i18n/I18nContext.jsx";
import { useAskSubmit } from "./useAskSubmit.js";
import { ChatComposer } from "./ChatComposer.jsx";
import { ChatMessageThread } from "./ChatMessageThread.jsx";
import { ChatSessionSidebar } from "./ChatSessionSidebar.jsx";
import { normalizeWorkListItem } from "./workListLabel.js";
import { getWorkspace } from "../../utils/workspaceStore.js";

/** Fixed retrieval depth for API compatibility (no UI control). */
const ASK_DEFAULT_TOP_K = 5;

export default function AskPanel({
  scopedWorkId = null,
  initialWorkId = "",
  showPageChrome = true,
  workspaceWorkId = null,
  workspaceId = "",
  urlSessionId = "",
  onUrlSessionIdChange,
  fillAvailableHeight = false,
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
  /** Server session sync: preference only (no UI toggle); list/patch when enabled. */
  const [serverSync] = useState(() => readAskServerSyncPref());
  const [agentToolTrace, setAgentToolTrace] = useState([]);
  const [streamEvents, setStreamEvents] = useState([]);
  /** Optional hint for POST /v2/agent/query (does not force routing). */
  const [answerClassHint, setAnswerClassHint] = useState("");
  const [pendingUserQuery, setPendingUserQuery] = useState("");
  const skipHydrateWorkRef = useRef(false);
  /** Last stream error message (React state can lag one frame when submit returns null). */
  const streamFailureRef = useRef("");

  const scopeKey = useMemo(() => deriveAskScopeKey({ locked, scopedWorkId, workspaceId }), [locked, scopedWorkId, workspaceId]);
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
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setWorkId(locked ? String(scopedWorkId).trim() : initialWorkId || "");
  }, [locked, scopedWorkId, initialWorkId]);

  useEffect(() => {
    migrateLegacyAskHistoryToSessions(scopeKey, (item) => (locked ? String(item.workId || "").trim() === String(scopedWorkId || "").trim() : true));
    getActiveSessionEntries(scopeKey);
    // eslint-disable-next-line react-hooks/set-state-in-effect
    bumpSessions();
  }, [scopeKey, locked, scopedWorkId, bumpSessions]);

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
          const rawFail = String(streamFailureRef.current || "").trim();
          streamFailureRef.current = "";
          const failMsg = rawFail || t("askPanel.agentIncompleteTurn");
          if (!rawFail) {
            setError(failMsg);
          }
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
          appendAskSessionTurn(scopeKey, turn);
          const sid = readAskSessionUi(scopeKey).activeId;
          const entriesAfter = getActiveSessionEntries(scopeKey);
          if (sid && entriesAfter.length === 1 && q) {
            const autoTitle = q.slice(0, 56) + (q.length > 56 ? "…" : "");
            renameAskSession(scopeKey, sid, autoTitle);
            if (serverSync && isServerAskSessionId(sid)) {
              try {
                await patchAskSessionRequest(scopeKey, sid, { title: autoTitle, active: true });
              } catch {
                /* non-fatal */
              }
            }
          }
          setNormalized(null);
          setQuery("");
          bumpSessions();
          if (serverSync) {
            const { activeId: sid2 } = readAskSessionUi(scopeKey);
            if (sid2 && isServerAskSessionId(sid2)) {
              try {
                await patchAskSessionRequest(scopeKey, sid2, { turns: entriesToApiTurns(getActiveSessionEntries(scopeKey)), active: true });
              } catch {
                /* non-fatal */
              }
            }
          }
          return;
        }
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
        appendAskSessionTurn(scopeKey, turn);
        const sid = readAskSessionUi(scopeKey).activeId;
        const entriesAfter = getActiveSessionEntries(scopeKey);
        if (sid && entriesAfter.length === 1 && q) {
          const autoTitle = q.slice(0, 56) + (q.length > 56 ? "…" : "");
          renameAskSession(scopeKey, sid, autoTitle);
          if (serverSync && isServerAskSessionId(sid)) {
            try {
              await patchAskSessionRequest(scopeKey, sid, { title: autoTitle, active: true });
            } catch {
              /* non-fatal */
            }
          }
        }
        setNormalized(null);
        setQuery("");
        bumpSessions();
        if (!serverSync) return;
        const { activeId: sid2 } = readAskSessionUi(scopeKey);
        if (sid2 && isServerAskSessionId(sid2)) {
          try {
            await patchAskSessionRequest(scopeKey, sid2, { turns: entriesToApiTurns(getActiveSessionEntries(scopeKey)), active: true });
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
      scopeKey,
      bumpSessions,
      serverSync,
      t,
    ],
  );

  const onActiveSessionChange = useCallback(
    async (sessionId) => {
      setActiveAskSession(scopeKey, sessionId);
      bumpSessions();
      onUrlSessionIdChange?.(sessionId);
      if (serverSync && sessionId && isServerAskSessionId(sessionId)) {
        try {
          await patchAskSessionRequest(scopeKey, sessionId, { active: true });
        } catch {
          /* non-fatal */
        }
      }
    },
    [scopeKey, bumpSessions, onUrlSessionIdChange, serverSync],
  );

  const onNewSession = useCallback(async () => {
    if (serverSync) {
      try {
        await createAskSessionRequest(scopeKey, {});
        const res = await listAskSessionsRequest(scopeKey);
        replaceScopeBundle(scopeKey, apiSessionsToBundle(res.data));
        bumpSessions();
        const aid = res.data?.active_session_id;
        if (aid) onUrlSessionIdChange?.(String(aid));
      } catch (err) {
        setError(formatResearchApiError(err));
      }
      return;
    }
    const id = createAskSession(scopeKey);
    bumpSessions();
    if (id) onUrlSessionIdChange?.(id);
  }, [serverSync, scopeKey, bumpSessions, onUrlSessionIdChange]);

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

  return (
    <Box
      sx={{
        width: "100%",
        boxSizing: "border-box",
        display: "flex",
        flexDirection: "column",
        ...(fillAvailableHeight
          ? { flex: 1, minHeight: 0, height: "100%" }
          : {
              minHeight: { xs: "min(100dvh - 140px, 720px)", md: "min(calc(100dvh - 160px), 900px)" },
              maxHeight: { md: "calc(100dvh - 160px)" },
            }),
      }}
    >
      <Box
        sx={{
          flex: 1,
          minHeight: 0,
          display: "flex",
          flexDirection: { xs: "column", md: "row" },
          gap: { xs: 1.5, md: 2 },
          alignItems: "stretch",
        }}
      >
        <ChatSessionSidebar
          t={t}
          sessionList={sessionList}
          activeSessionId={activeSessionId}
          onActiveSessionChange={onActiveSessionChange}
          onNewSession={onNewSession}
          sx={{ flex: { xs: "0 0 auto", md: "0 0 auto" }, maxHeight: { xs: "min(40vh, 320px)", md: "none" } }}
        />
        <Box sx={{ flex: 1, minWidth: 0, minHeight: 0, display: "flex", flexDirection: "column", gap: 0.5 }}>
          {showPageChrome ? (
            <>
              <Typography sx={{ fontWeight: 600, mb: 0.5, color: "rgba(255,255,255,0.9)" }}>{t("askPanel.chromeTitle")}</Typography>
              <Typography sx={{ color: "rgba(255,255,255,0.55)", fontSize: "0.8125rem", mb: 1 }}>{t("askPanel.chromeBody")}</Typography>
            </>
          ) : (
            <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", mb: 0.5, flexShrink: 0 }} noWrap title={scopeEyebrow}>
              {scopeEyebrow}
            </Typography>
          )}
          {error ? (
            <Alert severity="error" sx={{ fontSize: "0.8125rem", flexShrink: 0, py: 0.5 }}>
              {error}
            </Alert>
          ) : null}
          <ChatMessageThread
            t={t}
            history={history}
            pendingUserQuery={pendingUserQuery}
            isLoading={isLoading}
            streamEvents={streamEvents}
            liveNormalized={normalized}
            locked={locked}
            inWorkspace={inWorkspace}
            workId={workId}
            workspaceWorkId={workspaceWorkId}
            agentToolTrace={agentToolTrace}
            retrievalJsonOpen={retrievalJsonOpen}
            onToggleRetrievalJson={() => setRetrievalJsonOpen((v) => !v)}
            starterPromptKeys={starterPromptKeys}
            onStarterPrompt={setQuery}
          />
          <ChatComposer
            t={t}
            query={query}
            onQueryChange={setQuery}
            loading={isLoading}
            onSubmit={onSubmit}
            inWorkspace={inWorkspace}
            standaloneChatPath={standaloneChatPath}
            locked={locked}
            scopedWorkId={scopedWorkId}
            workspaceId={workspaceId}
            workId={workId}
            onWorkIdChange={handleWorkIdChange}
            onArticlePicked={onArticlePicked}
            onWorkSearch={searchWorks}
            resolvedWork={workDetailsForChip}
            corpusWorkspaceOnly={corpusWorkspaceOnly}
            standaloneMode={standaloneMode}
            answerClassHint={answerClassHint}
            onAnswerClassHintChange={setAnswerClassHint}
          />
        </Box>
      </Box>
    </Box>
  );
}
