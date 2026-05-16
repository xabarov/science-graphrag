import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";

import { useI18n } from "../../../../i18n/useI18n.js";
import { CHAT_PATH } from "../../../../routes/paths.js";
import { readAskServerSyncPref } from "../session/askSessionServerBridge.js";
import { deriveAskScopeKey, readAskSessionUi } from "../session/askSessionState.js";
import { buildStandaloneTracePath } from "../../traceability/traceabilityState.js";
import { readAskComposerPrefs, writeAskComposerPrefs } from "../chat/askComposerPreferences.js";
import { useAskSubmit } from "./useAskSubmit.js";
import { useAskSessionLifecycle } from "./useAskSessionLifecycle.js";
import { useAskPanelSessionHandlers } from "./useAskPanelSessionHandlers.js";
import { useAskWorkContext } from "./useAskWorkContext.js";
import { useAskPerformAgentSubmit } from "./useAskPerformAgentSubmit.js";
import { formatAskAgentUiError } from "./askAgentUiErrors.js";
import { deriveAskPanelScopeEyebrow } from "./askPanelScopePresentation.js";
import {
  extractPdfReadArtifactIdFromStreamEvents,
  PDF_READ_USER_MESSAGE_TOKEN,
} from "../../../../services/research/pdfReadUi.js";
import { useAskPanelClipboard } from "./useAskPanelClipboard.js";
import { useAskPanelStreamArtifacts } from "./useAskPanelStreamArtifacts.js";

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
  const [composerPrefs, setComposerPrefs] = useState(() =>
    readAskComposerPrefs(deriveAskScopeKey({ locked, scopedWorkId, workspaceId })),
  );
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
  const streamFailureRef = useRef("");
  const [pdfReadState, setPdfReadState] = useState({
    isActive: false,
    url: "",
    error: "",
    mode: "",
    artifactId: "",
  });
  /** When storage head matches this turn id, do not refill composer from `recent[0]` (avoids scopeKey churn after submit). */
  const composerSuppressHydrateTurnIdRef = useRef("");

  const { workDetailsForChip, workspaceSearchOptions, searchWorks, onArticlePicked, handleWorkIdChange } = useAskWorkContext({
    workspaceId,
    locked,
    workId,
    setWorkId,
  });

  const { onCopyUserText, onCopyAssistantEntry } = useAskPanelClipboard();

  const scopeKey = useMemo(() => deriveAskScopeKey({ locked, scopedWorkId, workspaceId }), [locked, scopedWorkId, workspaceId]);
  /**
   * Invariant: after any `await` (agent stream, patch), never use `scopeKey` from the outer `useCallback`
   * closure for localStorage / API scope — it can lag behind `deriveAskScopeKey` when URL or
   * `activeWorkspaceId` resolves mid-flight. Read `scopeKeyRef.current` instead.
   */
  const scopeKeyRef = useRef(scopeKey);
  useLayoutEffect(() => {
    scopeKeyRef.current = scopeKey;
  }, [scopeKey]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reload prefs when Ask scope changes
    setComposerPrefs(readAskComposerPrefs(scopeKey));
  }, [scopeKey]);
  const bumpSessions = useCallback(() => setSessionTick((v) => v + 1), []);
  const setWebResearchEnabled = useCallback(
    (next) => {
      setComposerPrefs((prev) => {
        const merged = { ...prev, webResearchEnabled: Boolean(next) };
        writeAskComposerPrefs(scopeKeyRef.current, merged);
        return merged;
      });
    },
    [],
  );
  const setAgentMode = useCallback((next) => {
    const mode = next === "plan" ? "plan" : "agent";
    setComposerPrefs((prev) => {
      const merged = { ...prev, agentMode: mode };
      writeAskComposerPrefs(scopeKeyRef.current, merged);
      return merged;
    });
  }, []);
  const { activeId: activeSessionId, sessions: sessionList } = readAskSessionUi(scopeKey, sessionTick);
  const inWorkspace = Boolean(workspaceWorkId && String(workspaceWorkId).trim());
  const corpusWorkspaceOnly = Boolean(String(workspaceId || "").trim() && !String(workId || "").trim() && !locked);
  const standaloneMode = !inWorkspace && !locked && !corpusWorkspaceOnly;

  useAskSessionLifecycle({
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
    setWorkId,
    composerSuppressHydrateTurnIdRef,
  });

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
      const formatted = formatAskAgentUiError(t, msg);
      streamFailureRef.current = formatted;
      setError(formatted);
    },
  });

  const { webResearchEnabled, agentMode } = composerPrefs;

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setWorkId(locked ? String(scopedWorkId).trim() : initialWorkId || "");
  }, [locked, scopedWorkId, initialWorkId]);

  const performAgentSubmit = useAskPerformAgentSubmit({
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
  });

  const {
    researchPlanForPanel,
    researchPlanStreamHint,
    openStructuredQuestion,
    onStructuredAnswersSubmit,
  } = useAskPanelStreamArtifacts({
    t,
    normalized,
    history,
    streamEvents,
    performAgentSubmit,
  });

  const onSubmit = useCallback(
    async (e) => {
      e.preventDefault();
      if (openStructuredQuestion) return;
      await performAgentSubmit(String(query || "").trim());
    },
    [query, performAgentSubmit, openStructuredQuestion],
  );

  const {
    onRestartFromTurn,
    onClearChat,
    onDeleteSession,
    onDeleteTurn,
    onActiveSessionChange,
    onNewSession,
  } = useAskPanelSessionHandlers({
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
  });

  const standaloneChatPath = buildStandaloneTracePath(CHAT_PATH, workId);

  const scopeEyebrow = deriveAskPanelScopeEyebrow(t, { inWorkspace, locked, corpusWorkspaceOnly });

  const streamingHint = useMemo(() => {
    if (!isLoading || !streamingTarget) return "";
    if (streamingTarget.scopeKey !== scopeKey) return "";
    if (String(streamingTarget.sessionId || "") !== String(activeSessionId || "")) return "";
    return t("askPanel.agentStreamingHint");
  }, [isLoading, streamingTarget, scopeKey, activeSessionId, t]);

  const pdfReadingMode = useMemo(
    () =>
      String(
        normalized?.run_metadata?.agent_tools?.effective?.resolved_pdf_reading_mode ??
          normalized?.run_metadata?.request_pdf_reading_mode ??
          "ask",
      ),
    [normalized],
  );

  const onReadPdfSource = useCallback(
    async (pdfUrlRaw) => {
      const pdfUrl = String(pdfUrlRaw || "").trim();
      if (!pdfUrl || isLoading || pdfReadingMode === "off") return;
      setPdfReadState({ isActive: true, url: pdfUrl, error: "", mode: "running", artifactId: "" });
      try {
        const res = await performAgentSubmit(PDF_READ_USER_MESSAGE_TOKEN, {
          pdfReadRequest: { pdf_url: pdfUrl },
        });
        const streamEvents = res && typeof res === "object" && Array.isArray(res.streamEvents) ? res.streamEvents : [];
        const fromStream = extractPdfReadArtifactIdFromStreamEvents(streamEvents);
        const rm =
          res && typeof res === "object" && res.ok !== false && res.normalized?.run_metadata != null
            ? res.normalized.run_metadata
            : null;
        const fromMeta =
          rm && typeof rm === "object" && rm.pdf_read_artifact_id != null
            ? String(rm.pdf_read_artifact_id).trim()
            : "";
        const artifactId = fromMeta || fromStream;

        if (!res || res.ok === false) {
          setPdfReadState({
            isActive: false,
            url: pdfUrl,
            error: t("askPanel.agentIncompleteTurn"),
            mode: "failed",
            artifactId,
          });
          return;
        }

        setPdfReadState({
          isActive: false,
          url: pdfUrl,
          error: "",
          mode: "done",
          artifactId,
        });
      } catch (exc) {
        setPdfReadState({
          isActive: false,
          url: pdfUrl,
          error: formatAskAgentUiError(t, String(exc?.message || exc || "")),
          mode: "failed",
          artifactId: "",
        });
      }
    },
    [isLoading, pdfReadingMode, performAgentSubmit, t],
  );

  /** @see ./askPanelOrchestrationContract.js — keep `ASK_PANEL_ORCHESTRATION_RETURN_KEYS` aligned when changing this object. */
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
    workspaceSearchOptions,
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
    pdfReadingMode,
    onReadPdfSource,
    pdfReadState,
    webResearchEnabled,
    agentMode,
    setWebResearchEnabled,
    setAgentMode,
  };
}
