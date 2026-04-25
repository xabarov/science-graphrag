import React, { useCallback, useEffect, useMemo, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { isAdminModeEnabled } from "../layout/adminVisibility.js";
import WorkIdGlossaryHint from "../layout/WorkIdGlossaryHint.jsx";
import { buildQueryBody, createAskSession as createAskSessionRequest, formatResearchApiError, getWorks, listAskSessions as listAskSessionsRequest, patchAskSession as patchAskSessionRequest } from "../../services/researchApi.js";
import { apiSessionsToBundle, entriesToApiTurns, isServerAskSessionId, readAskServerSyncPref, writeAskServerSyncPref } from "./askSessionServerBridge.js";
import { rememberAskHistory } from "./askHistoryState.js";
import { appendAskSessionTurn, createAskSession, deriveAskScopeKey, getActiveSessionEntries, migrateLegacyAskHistoryToSessions, readAskSessionUi, renameAskSession, replaceScopeBundle, sessionExistsInScope, setActiveAskSession } from "./askSessionState.js";
import { buildStandaloneTracePath } from "./traceabilityState.js";
import { persistWorkId } from "../../pages/WorkspacePage/utils/workContext.js";
import { useI18n } from "../../i18n/I18nContext.jsx";
import { AskAnswerPanel } from "./AskAnswerPanel.jsx";
import { AskSessionControls } from "./AskSessionControls.jsx";
import { useAskSubmit } from "./useAskSubmit.js";

export default function AskPanel({ scopedWorkId = null, initialWorkId = "", showPageChrome = true, workspaceWorkId = null, workspaceId = "", urlSessionId = "", onUrlSessionIdChange, labMode = false }) {
  const { t } = useI18n();
  const locked = Boolean(scopedWorkId && String(scopedWorkId).trim());
  const [query, setQuery] = useState("object detection benchmarks");
  const [workId, setWorkId] = useState(locked ? String(scopedWorkId).trim() : initialWorkId);
  const [workOptions, setWorkOptions] = useState([]);
  const [topK, setTopK] = useState("5");
  const [error, setError] = useState(null);
  const [normalized, setNormalized] = useState(null);
  const [history, setHistory] = useState([]);
  const [retrievalJsonOpen, setRetrievalJsonOpen] = useState(false);
  const [sessionTick, setSessionTick] = useState(0);
  const [sessionTitleDraft, setSessionTitleDraft] = useState("");
  const [serverSync, setServerSync] = useState(() => readAskServerSyncPref());
  const [retrievalMode, setRetrievalMode] = useState(() => "vector");
  const [agentToolTrace, setAgentToolTrace] = useState([]);
  const [streamEvents, setStreamEvents] = useState([]);
  const retrievalLabVisible = Boolean(labMode || isAdminModeEnabled());

  const scopeKey = useMemo(() => deriveAskScopeKey({ locked, scopedWorkId, workspaceId }), [locked, scopedWorkId, workspaceId]);
  const bumpSessions = useCallback(() => setSessionTick((v) => v + 1), []);
  const { activeId: activeSessionId, sessions: sessionList } = readAskSessionUi(scopeKey, sessionTick);
  const activeSessionMeta = useMemo(() => sessionList.find((s) => s.id === activeSessionId), [sessionList, activeSessionId]);
  const inWorkspace = Boolean(workspaceWorkId && String(workspaceWorkId).trim());
  const corpusWorkspaceOnly = Boolean(String(workspaceId || "").trim() && !String(workId || "").trim() && !locked);
  const standaloneMode = !inWorkspace && !locked && !corpusWorkspaceOnly;
  const bodyPreview = useMemo(() => buildQueryBody(query, workId, topK, workspaceId, retrievalLabVisible ? retrievalMode : "vector"), [query, workId, topK, workspaceId, retrievalMode, retrievalLabVisible]);

  const { submit, isLoading } = useAskSubmit({
    workspaceId,
    onStart: () => {
      setError(null);
      setNormalized(null);
      setRetrievalJsonOpen(false);
      setAgentToolTrace([]);
      setStreamEvents([]);
    },
    onResult: setNormalized,
    onToolTrace: setAgentToolTrace,
    onStreamEvent: (event) => {
      if (event?.type === "tool_call" || event?.type === "tool_result") {
        setStreamEvents((prev) => [...prev, event]);
      }
    },
    onError: setError,
  });

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSessionTitleDraft(activeSessionMeta?.title || "");
  }, [activeSessionMeta?.title, activeSessionId]);

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
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTopK(String(recent[0].topK || 5));
  }, [locked, initialWorkId, scopeKey]);

  useEffect(() => {
    let cancelled = false;
    getWorks({ limit: 80, offset: 0 })
      .then((res) => {
        if (!cancelled) setWorkOptions(res.data?.items || []);
      })
      .catch(() => {
        if (!cancelled) setWorkOptions([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!locked && workId.trim()) persistWorkId(workId);
  }, [locked, workId]);

  const onSubmit = useCallback(async (e) => {
    e.preventDefault();
    const nextNormalized = await submit({ query, topK, retrievalMode, retrievalLabVisible, bodyPreview });
    if (!nextNormalized) return;
    const queryMode = locked || inWorkspace ? "workspace" : corpusWorkspaceOnly ? "workspace_corpus" : workId ? "scoped" : "global";
    const turn = { query, workId, topK, answer: nextNormalized.answer, citationCount: nextNormalized.citations.length, mode: queryMode };
    rememberAskHistory(turn);
    appendAskSessionTurn(scopeKey, turn);
    bumpSessions();
    if (!serverSync) return;
    const { activeId: sid } = readAskSessionUi(scopeKey);
    if (sid && isServerAskSessionId(sid)) {
      try {
        await patchAskSessionRequest(scopeKey, sid, { turns: entriesToApiTurns(getActiveSessionEntries(scopeKey)), active: true });
      } catch {
        /* non-fatal */
      }
    }
  }, [submit, query, topK, retrievalMode, retrievalLabVisible, bodyPreview, locked, inWorkspace, corpusWorkspaceOnly, workId, scopeKey, bumpSessions, serverSync]);

  const onActiveSessionChange = useCallback(async (sessionId) => {
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
  }, [scopeKey, bumpSessions, onUrlSessionIdChange, serverSync]);

  const onSessionTitleCommit = useCallback(async () => {
    const next = sessionTitleDraft.trim();
    if (!activeSessionId || !next || next === (activeSessionMeta?.title || "").trim()) return;
    renameAskSession(scopeKey, activeSessionId, next);
    bumpSessions();
    if (serverSync && isServerAskSessionId(activeSessionId)) {
      try {
        await patchAskSessionRequest(scopeKey, activeSessionId, { title: next, active: true });
      } catch {
        /* non-fatal */
      }
    }
  }, [sessionTitleDraft, activeSessionId, activeSessionMeta?.title, scopeKey, bumpSessions, serverSync]);

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

  return (
    <Box sx={{ width: "100%", boxSizing: "border-box" }}>
      {showPageChrome ? (<><Typography sx={{ fontWeight: 600, mb: 1, color: "rgba(255,255,255,0.9)" }}>{t("askPanel.chromeTitle")}</Typography><Typography sx={{ color: "rgba(255,255,255,0.6)", fontSize: "0.8125rem", mb: 2 }}>{t("askPanel.chrome.p1")}<code style={{ color: "rgba(129,140,248,0.95)" }}>VITE_API_BASE_URL</code>{t("askPanel.chrome.p2")}</Typography></>) : (<Box sx={{ mb: 2, p: 1.25, borderRadius: "6px", border: "1px solid rgba(99,102,241,0.2)", backgroundColor: "rgba(99,102,241,0.08)" }}><Typography sx={{ color: "rgba(129,140,248,0.95)", fontSize: "0.75rem", mb: 0.5 }}>{inWorkspace || locked ? t("askPanel.banner.workspaceScoped") : corpusWorkspaceOnly ? t("askPanel.banner.workspaceCorpusTitle") : t("askPanel.banner.standalone")}</Typography><Typography sx={{ color: "rgba(255,255,255,0.78)", fontSize: "0.8125rem" }}>{inWorkspace || locked ? t("askPanel.banner.descWorkspace") : corpusWorkspaceOnly ? t("askPanel.banner.descWorkspaceCorpus") : t("askPanel.banner.descStandalone")}</Typography></Box>)}
      {!locked && !workId.trim() ? (<Box sx={{ mb: 2, p: 1.5, borderRadius: "6px", border: "1px dashed rgba(255,255,255,0.12)", backgroundColor: "rgba(255,255,255,0.02)" }}><Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: "rgba(255,255,255,0.85)" }}>{t("askPanel.optionalContext.title")}</Typography><Typography sx={{ mt: 0.6, fontSize: "0.8125rem", color: "rgba(255,255,255,0.55)" }}><WorkIdGlossaryHint variant="ask" /></Typography></Box>) : null}
      {locked ? (<Box sx={{ mb: 2, p: 1.25, borderRadius: "6px", border: "1px solid rgba(255,255,255,0.08)", backgroundColor: "#1a1a1a" }}><Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)" }}>{t("askPanel.workIdScopeLabel")}</Typography><Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.85)", fontFamily: "monospace", mt: 0.25 }}>{workId}</Typography></Box>) : null}
      <AskSessionControls t={t} query={query} onQueryChange={setQuery} workId={workId} onWorkIdChange={setWorkId} workOptions={workOptions} topK={topK} onTopKChange={setTopK} retrievalLabVisible={retrievalLabVisible} retrievalMode={retrievalMode} onRetrievalModeChange={setRetrievalMode} loading={isLoading} onSubmit={onSubmit} inWorkspace={inWorkspace} standaloneAskPath={buildStandaloneTracePath("/ask", workId)} locked={locked} serverSync={serverSync} onServerSyncChange={(next) => { writeAskServerSyncPref(next); setServerSync(next); }} activeSessionId={activeSessionId} sessionList={sessionList} onActiveSessionChange={onActiveSessionChange} sessionTitleDraft={sessionTitleDraft} onSessionTitleDraftChange={setSessionTitleDraft} onSessionTitleCommit={onSessionTitleCommit} onNewSession={onNewSession} history={history} onRestoreFromHistory={(item) => { setQuery(item.query); if (!locked) setWorkId(item.workId); setTopK(String(item.topK)); }} standaloneMode={standaloneMode} onUrlSyncSupported={Boolean(onUrlSessionIdChange)} />
      {error ? <Alert severity="error" sx={{ mt: 2, fontSize: "0.8125rem" }}>{error}</Alert> : null}
      <AskAnswerPanel t={t} normalized={normalized} locked={locked} inWorkspace={inWorkspace} workId={workId} workspaceWorkId={workspaceWorkId} retrievalLabVisible={retrievalLabVisible} retrievalMode={retrievalMode} agentToolTrace={agentToolTrace} retrievalJsonOpen={retrievalJsonOpen} onToggleRetrievalJson={() => setRetrievalJsonOpen((v) => !v)} streamEvents={streamEvents} isStreaming={isLoading && streamEvents.length > 0} />
    </Box>
  );
}
