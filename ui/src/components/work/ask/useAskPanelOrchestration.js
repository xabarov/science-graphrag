import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  createAskSession as createAskSessionRequest,
  deleteAskSession as deleteAskSessionRequest,
  formatResearchApiError,
  getWorkDetail,
  getWorks,
  listAskSessions as listAskSessionsRequest,
  normalizeQueryResponse,
  patchAskSession as patchAskSessionRequest,
} from "../../../services/researchApi.js";
import { useI18n } from "../../../i18n/useI18n.js";
import { persistWorkId } from "../../../pages/WorkspacePage/utils/workContext.js";
import { CHAT_PATH } from "../../../routes/paths.js";
import { getWorkspace } from "../../../utils/workspaceStore.js";
import {
  apiSessionsToBundle,
  entriesToApiTurns,
  isServerAskSessionId,
  readAskServerSyncPref,
} from "./askSessionServerBridge.js";
import { extractOpenStructuredQuestion, extractResearchPlanStreamHint } from "./askStreamArtifacts.js";
import { rememberAskHistory } from "./askHistoryState.js";
import {
  appendAskSessionTurn,
  appendAskSessionTurnToSession,
  buildAgentHistoryDigest,
  createAskSession,
  deriveAskScopeKey,
  getActiveSessionEntries,
  getAskSessionEntries,
  migrateLegacyAskHistoryToSessions,
  maybeMigrateStandaloneBundleToWorkspaceScope,
  readAskSessionUi,
  removeAskSession,
  removeAskSessionTurn,
  renameAskSession,
  replaceScopeBundle,
  sessionExistsInScope,
  setActiveAskSession,
  truncateAskSessionFromTurn,
} from "./askSessionState.js";
import { buildStandaloneTracePath } from "../traceability/traceabilityState.js";
import { useAskSubmit } from "./useAskSubmit.js";
import { copyToClipboard } from "../../../utils/copyToClipboard.js";
import { useFeedback } from "../../feedback/index.js";
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
  const { showToast } = useFeedback();
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
  const [pendingUserQuery, setPendingUserQuery] = useState("");
  /** While a run is in flight: scope + session the submit belongs to (survives sidebar switches). */
  const [streamingTarget, setStreamingTarget] = useState(null);
  const skipHydrateWorkRef = useRef(false);
  const streamFailureRef = useRef("");
  /** When storage head matches this turn id, do not refill composer from `recent[0]` (avoids scopeKey churn after submit). */
  const composerSuppressHydrateTurnIdRef = useRef("");

  const formatAgentUiError = useCallback(
    (msg) => {
      const s = String(msg || "").trim();
      if (!s) return t("askPanel.agentIncompleteTurn");
      if (/\(code 403\)/.test(s) || (/403/.test(s) && /Upstream LLM/i.test(s))) return t("chat.errors.llmForbidden");
      if (/\(code 401\)/.test(s) || (/401/.test(s) && /Upstream LLM/i.test(s))) return t("chat.errors.llmUnauthorized");
      return s;
    },
    [t],
  );

  const onCopyUserText = useCallback(
    async (text) => {
      const ok = await copyToClipboard(String(text || ""));
      showToast(t(ok ? "chat.copy.success" : "chat.copy.failed"));
    },
    [showToast, t],
  );

  const onCopyAssistantEntry = useCallback(
    async (entry) => {
      let plain = "";
      if (entry?.details && typeof entry.details === "object") {
        plain = String(entry.details.answer ?? "");
      } else {
        plain = String(entry?.answer ?? "");
      }
      const ok = await copyToClipboard(plain);
      showToast(t(ok ? "chat.copy.success" : "chat.copy.failed"));
    },
    [showToast, t],
  );

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

  const { submit, isLoading, abort } = useAskSubmit({
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
      const formatted = formatAgentUiError(msg);
      streamFailureRef.current = formatted;
      setError(formatted);
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
    const headId = String(recent[0].id || "");
    if (headId && headId === composerSuppressHydrateTurnIdRef.current) {
      return;
    }
    composerSuppressHydrateTurnIdRef.current = "";
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

  const performAgentSubmit = useCallback(
    async (queryText, { workIdForTurn, userStructuredAnswer } = {}) => {
      const q = String(queryText || "").trim();
      if (!q) return;
      const turnWorkId = workIdForTurn != null ? String(workIdForTurn).trim() : String(workId || "").trim();
      const submitSk = scopeKeyRef.current;
      const submitSid = String(activeSessionId || "").trim();
      setStreamingTarget({ scopeKey: submitSk, sessionId: submitSid });
      setPendingUserQuery(q);
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
          });
        } catch (submitExc) {
          composerSuppressHydrateTurnIdRef.current = "";
          setQuery(q);
          throw submitExc;
        }
        const queryMode =
          locked || inWorkspace ? "workspace" : corpusWorkspaceOnly ? "workspace_corpus" : turnWorkId ? "scoped" : "global";
        if (!pack?.normalized) {
          const sk = submitSk;
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
          const persistedStreamEvents = Array.isArray(pack?.streamEvents) ? pack.streamEvents : [];
          const persistedToolTrace = Array.isArray(pack?.agentToolTrace) ? pack.agentToolTrace : [];
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
            product_path: nextNormalized.product_path ?? null,
            product_markers: Array.isArray(nextNormalized.product_markers) ? nextNormalized.product_markers : [],
            stream_events: persistedStreamEvents.slice(-80),
            agent_tool_trace: persistedToolTrace,
            open_structured_question: extractOpenStructuredQuestion(persistedStreamEvents),
          };
          const turn = {
            query: q,
            workId: turnWorkId,
            topK: ASK_DEFAULT_TOP_K,
            answer: failMsg,
            citationCount: 0,
            mode: queryMode,
            details,
          };
          rememberAskHistory(turn);
          if (submitSid) {
            appendAskSessionTurnToSession(sk, submitSid, turn);
          } else {
            appendAskSessionTurn(sk, turn);
          }
          const currentSk = scopeKeyRef.current;
          const { activeId: currentActive } = readAskSessionUi(currentSk);
          const viewingThisRun = currentSk === sk && String(currentActive || "") === submitSid;
          if (viewingThisRun) {
            setHistory(submitSid ? getAskSessionEntries(sk, submitSid) : getActiveSessionEntries(sk));
          }
          const entriesAfter = submitSid ? getAskSessionEntries(sk, submitSid) : getActiveSessionEntries(sk);
          composerSuppressHydrateTurnIdRef.current = String(entriesAfter[0]?.id || "");
          if (submitSid && entriesAfter.length === 1 && q) {
            const autoTitle = q.slice(0, 56) + (q.length > 56 ? "…" : "");
            renameAskSession(sk, submitSid, autoTitle);
            if (serverSync && isServerAskSessionId(submitSid)) {
              try {
                await patchAskSessionRequest(sk, submitSid, { title: autoTitle, active: viewingThisRun });
              } catch {
                /* non-fatal */
              }
            }
          }
          setNormalized(null);
          bumpSessions();
          if (serverSync && submitSid && isServerAskSessionId(submitSid)) {
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
          return;
        }
        const sk = submitSk;
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
          product_path: nextNormalized.product_path ?? null,
          product_markers: Array.isArray(nextNormalized.product_markers) ? nextNormalized.product_markers : [],
          stream_events: persistedStreamEvents.slice(-80),
          agent_tool_trace: persistedToolTrace,
          open_structured_question: extractOpenStructuredQuestion(persistedStreamEvents),
        };
        const turn = {
          query: q,
          workId: turnWorkId,
          topK: ASK_DEFAULT_TOP_K,
          answer: nextNormalized.answer,
          citationCount: nextNormalized.citations.length,
          mode: queryMode,
          details,
        };
        rememberAskHistory(turn);
        if (submitSid) {
          appendAskSessionTurnToSession(sk, submitSid, turn);
        } else {
          appendAskSessionTurn(sk, turn);
        }
        const currentSk = scopeKeyRef.current;
        const { activeId: currentActive } = readAskSessionUi(currentSk);
        const viewingThisRun = currentSk === sk && String(currentActive || "") === submitSid;
        if (viewingThisRun) {
          setHistory(submitSid ? getAskSessionEntries(sk, submitSid) : getActiveSessionEntries(sk));
        }
        const entriesAfter = submitSid ? getAskSessionEntries(sk, submitSid) : getActiveSessionEntries(sk);
        composerSuppressHydrateTurnIdRef.current = String(entriesAfter[0]?.id || "");
        if (submitSid && entriesAfter.length === 1 && q) {
          const autoTitle = q.slice(0, 56) + (q.length > 56 ? "…" : "");
          renameAskSession(sk, submitSid, autoTitle);
          if (serverSync && isServerAskSessionId(submitSid)) {
            try {
              await patchAskSessionRequest(sk, submitSid, { title: autoTitle, active: viewingThisRun });
            } catch {
              /* non-fatal */
            }
          }
        }
        setNormalized(null);
        bumpSessions();
        if (!serverSync) return;
        if (submitSid && isServerAskSessionId(submitSid)) {
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
      } finally {
        setPendingUserQuery("");
        setStreamingTarget(null);
      }
    },
    [
      submit,
      workId,
      activeSessionId,
      locked,
      inWorkspace,
      corpusWorkspaceOnly,
      bumpSessions,
      serverSync,
      t,
    ],
  );

  const researchPlanForPanel = useMemo(() => {
    const rm =
      normalized && typeof normalized === "object" && normalized.run_metadata && typeof normalized.run_metadata === "object"
        ? normalized.run_metadata
        : null;
    if (rm?.research_plan && typeof rm.research_plan === "object") return rm.research_plan;
    const h0 = history[0];
    const hrm = h0?.details?.run_metadata;
    if (hrm && typeof hrm === "object" && hrm.research_plan && typeof hrm.research_plan === "object") return hrm.research_plan;
    return null;
  }, [normalized, history]);

  const researchPlanStreamHint = useMemo(() => extractResearchPlanStreamHint(streamEvents), [streamEvents]);

  const openStructuredQuestion = useMemo(() => {
    const head = history[0];
    const d = head?.details;
    const fromEvents = Array.isArray(d?.stream_events) ? extractOpenStructuredQuestion(d.stream_events) : null;
    if (fromEvents) return fromEvents;
    if (d?.open_structured_question && typeof d.open_structured_question === "object") {
      const rq = d.open_structured_question;
      if (Array.isArray(rq.questions) && rq.questions.length && String(rq.request_id || "").trim()) {
        return rq;
      }
    }
    return null;
  }, [history]);

  const onStructuredAnswersSubmit = useCallback(
    async (payload) => {
      const rid = String(payload?.request_id || "").trim();
      const answers = Array.isArray(payload?.answers) ? payload.answers : [];
      if (!rid || !answers.length) return;
      await performAgentSubmit(t("askPanel.userQuestion.continuePlaceholder"), {
        userStructuredAnswer: { request_id: rid, answers },
      });
    },
    [performAgentSubmit, t],
  );

  const onSubmit = useCallback(
    async (e) => {
      e.preventDefault();
      if (openStructuredQuestion) return;
      await performAgentSubmit(String(query || "").trim());
    },
    [query, performAgentSubmit, openStructuredQuestion],
  );

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
    [abort, activeSessionId, bumpSessions, isLoading, performAgentSubmit, serverSync],
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
  }, [abort, bumpSessions, onUrlSessionIdChange, serverSync]);

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
    [abort, bumpSessions, onUrlSessionIdChange, serverSync],
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
    [abort, activeSessionId, bumpSessions, isLoading, serverSync],
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

  const streamingHint = useMemo(() => {
    if (!isLoading || !streamingTarget) return "";
    if (streamingTarget.scopeKey !== scopeKey) return "";
    if (String(streamingTarget.sessionId || "") !== String(activeSessionId || "")) return "";
    return t("askPanel.agentStreamingHint");
  }, [isLoading, streamingTarget, scopeKey, activeSessionId, t]);

  return {
    t,
    locked,
    scopedWorkId,
    workspaceId,
    scopeKey,
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
    pendingUserQuery,
    streamingTarget,
    inWorkspace,
    corpusWorkspaceOnly,
    standaloneMode,
    starterPromptKeys,
    isLoading,
    abort,
    onSubmit,
    onActiveSessionChange,
    onNewSession,
    onRestartFromTurn,
    onClearChat,
    onDeleteSession,
    onDeleteTurn,
    onCopyUserText,
    onCopyAssistantEntry,
    searchWorks,
    onArticlePicked,
    handleWorkIdChange,
    standaloneChatPath,
    scopeEyebrow,
    streamingHint,
    researchPlanForPanel,
    researchPlanStreamHint,
    openStructuredQuestion,
    onStructuredAnswersSubmit,
  };
}
