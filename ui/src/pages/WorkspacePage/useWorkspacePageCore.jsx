import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useTheme } from "@mui/material/styles";

import { useFeedback } from "../../components/feedback/index.js";
import { formatResearchApiError } from "../../services/researchApi.js";
import {
  setActiveWorkspaceId,
  getWorkspace,
  createWorkspace,
  addWorkToWorkspace,
  removeWorkFromWorkspace,
  startWorkspaceDocumentIngest,
  startWorkspaceBatchIngest,
  getWorkspaceGraphStats,
} from "../../utils/workspaceStore.js";
import { isAdminModeEnabled } from "../../components/layout/adminVisibility.js";
import { persistWorkId, resolveSelectedWorkId } from "./utils/workContext.js";
import { useI18n } from "../../i18n/useI18n.js";
import useJobStream from "../../hooks/useJobStream.js";
import { useWorkspacePapersModel } from "./useWorkspacePapersModel.js";
import { useWorkspaceIdeaAssist } from "./useWorkspaceIdeaAssist.js";
import { useWorkspaceLegacyRedirect } from "./useWorkspaceLegacyRedirect.js";
import { useWorkspaceSummary } from "./useWorkspaceSummary.js";
import { setPersistedIngestJobId } from "./workspaceIngestStorage.js";
import { useWorkspaceBootstrap } from "./useWorkspaceBootstrap.js";
import { useIngestDedupAutoOpen } from "./useIngestDedupAutoOpen.js";
import WorkspacePageEmptyState from "./WorkspacePageEmptyState.jsx";

export function useWorkspacePageCore() {
  const theme = useTheme();
  const { t } = useI18n();
  const { confirm, showToast } = useFeedback();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const workspaceIdFromUrl = (searchParams.get("workspace_id") || "").trim();
  const workIdFromUrl = (searchParams.get("work_id") || "").trim();

  useWorkspaceLegacyRedirect(searchParams, navigate);

  const [workspaceMeta, setWorkspaceMeta] = useState({ id: "", name: "", work_ids: [] });
  const [workspaceLoading, setWorkspaceLoading] = useState(true);
  const [workspaceError, setWorkspaceError] = useState(null);
  /** True when last workspace load failed with HTTP 5xx (e.g. 502) — drives server-specific recovery copy. */
  const [workspaceErrorIsServer, setWorkspaceErrorIsServer] = useState(false);
  const [workspaceLoadNonce, setWorkspaceLoadNonce] = useState(0);
  const [emptyCreateBusy, setEmptyCreateBusy] = useState(false);
  const [emptyCreateErr, setEmptyCreateErr] = useState(null);
  const [addWorkInput, setAddWorkInput] = useState("");
  const [addBusy, setAddBusy] = useState(false);
  const [addErr, setAddErr] = useState(null);

  const [ingestJobId, setIngestJobId] = useState("");
  const [ingestJob, setIngestJob] = useState(null);
  const [ingestErr, setIngestErr] = useState(null);
  const [ingestDedupPanelOpen, setIngestDedupPanelOpen] = useState(false);
  const [uploadBusy, setUploadBusy] = useState(false);
  const [graphStats, setGraphStats] = useState(null);
  const canUseIdeaAssist = useMemo(() => isAdminModeEnabled(), []);

  const {
    summaryOpen,
    setSummaryOpen,
    summaryBusy,
    summaryText,
    handleSummarizeWorkspace,
  } = useWorkspaceSummary(workspaceMeta.id, t);

  const {
    ideaOpen,
    setIdeaOpen,
    ideaBusy,
    ideaError,
    ideaResult,
    handleGenerateHypotheses,
  } = useWorkspaceIdeaAssist(workspaceMeta.id, canUseIdeaAssist);

  useWorkspaceBootstrap({
    workspaceIdFromUrl,
    workIdFromUrl,
    workspaceLoadNonce,
    setSearchParams,
    setWorkspaceMeta,
    setWorkspaceLoading,
    setWorkspaceError,
    setWorkspaceErrorIsServer,
    setIngestJobId,
    t,
  });

  const refreshWorkspaceMeta = useCallback(async () => {
    const id = workspaceMeta.id;
    if (!id) return;
    try {
      const ws = await getWorkspace(id);
      if (ws) setWorkspaceMeta(ws);
    } catch {
      /* ignore */
    }
  }, [workspaceMeta.id]);

  useEffect(() => {
    const id = String(workspaceMeta.id || "").trim();
    if (!id) {
      setGraphStats(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const s = await getWorkspaceGraphStats(id);
        if (!cancelled) setGraphStats(s);
      } catch {
        if (!cancelled) setGraphStats(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [workspaceMeta.id, workspaceMeta.work_ids]);

  useIngestDedupAutoOpen(workspaceMeta.id, setIngestDedupPanelOpen);

  const effectiveWorkIds = useMemo(() => {
    const fromWs = Array.isArray(workspaceMeta.work_ids) ? workspaceMeta.work_ids : [];
    if (fromWs.length) return fromWs;
    return [];
  }, [workspaceMeta.work_ids]);

  const selectedWorkId = useMemo(
    () => resolveSelectedWorkId({ workIds: effectiveWorkIds, workIdFromUrl }),
    [effectiveWorkIds, workIdFromUrl],
  );

  const { papers } = useWorkspacePapersModel({ effectiveWorkIds });

  const setWorkFocusInUrl = useCallback(
    (wid) => {
      const w = String(wid || "").trim();
      if (!workspaceMeta.id || !w) return;
      const p = new URLSearchParams();
      p.set("workspace_id", workspaceMeta.id);
      p.set("work_id", w);
      setSearchParams(p, { replace: true });
    },
    [workspaceMeta.id, setSearchParams],
  );

  useEffect(() => {
    if (selectedWorkId) persistWorkId(selectedWorkId);
  }, [selectedWorkId]);

  useJobStream({
    jobId: ingestJobId,
    enabled: Boolean(ingestJobId),
    onUpdate: useCallback((job) => setIngestJob(job), []),
    onTerminal: useCallback(
      async (job) => {
        await refreshWorkspaceMeta();
        const pc = job?.pending_conflicts;
        const pending =
          pc && typeof pc === "object"
            ? Number((pc.works || 0) + (pc.authors || 0) + (pc.entities || 0))
            : Number(job?.pending_conflicts_count || 0);
        if (String(job?.status || "") === "completed" && pending > 0) {
          setIngestDedupPanelOpen(true);
        }
        setPersistedIngestJobId(workspaceMeta.id, "");
        setIngestJobId("");
        setIngestJob(null);
      },
      [refreshWorkspaceMeta, workspaceMeta.id],
    ),
    onError: useCallback(
      (err, failCount) => {
        if (failCount >= 3) setIngestErr(formatResearchApiError(err));
      },
      [setIngestErr],
    ),
    fallbackPollMs: 2000,
  });

  const handleEmptyCreateWorkspace = useCallback(async () => {
    setEmptyCreateErr(null);
    setEmptyCreateBusy(true);
    try {
      const row = await createWorkspace("Workspace");
      if (row?.id) {
        setActiveWorkspaceId(row.id);
        const next = new URLSearchParams();
        next.set("workspace_id", row.id);
        setSearchParams(next, { replace: true });
      }
    } catch (err) {
      setEmptyCreateErr(formatResearchApiError(err));
    } finally {
      setEmptyCreateBusy(false);
    }
  }, [setSearchParams]);

  const emptyState = useMemo(
    () => (
      <WorkspacePageEmptyState
        t={t}
        theme={theme}
        emptyCreateBusy={emptyCreateBusy}
        emptyCreateErr={emptyCreateErr}
        onCreateWorkspace={handleEmptyCreateWorkspace}
      />
    ),
    [t, theme, emptyCreateBusy, emptyCreateErr, handleEmptyCreateWorkspace],
  );

  async function handleAddWork(e) {
    e?.preventDefault?.();
    const raw = addWorkInput.trim();
    if (!raw || !workspaceMeta.id) return;
    setAddBusy(true);
    setAddErr(null);
    try {
      await addWorkToWorkspace(workspaceMeta.id, raw);
      setAddWorkInput("");
      const ws = await getWorkspace(workspaceMeta.id);
      if (ws) setWorkspaceMeta(ws);
    } catch (err) {
      setAddErr(formatResearchApiError(err));
    } finally {
      setAddBusy(false);
    }
  }

  async function handleUploadDocument(ev) {
    const file = ev.target.files?.[0];
    ev.target.value = "";
    if (!file || !workspaceMeta.id) return;
    setUploadBusy(true);
    setIngestErr(null);
    try {
      const job = await startWorkspaceDocumentIngest(workspaceMeta.id, file);
      const jid = String(job?.job_id || "").trim();
      if (jid) {
        setIngestJob(job);
        setIngestJobId(jid);
        setPersistedIngestJobId(workspaceMeta.id, jid);
      }
    } catch (err) {
      setIngestErr(formatResearchApiError(err));
    } finally {
      setUploadBusy(false);
    }
  }

  async function handleUploadBatch(files, archive = null) {
    if (!workspaceMeta.id) return;
    const list = Array.isArray(files) ? files.filter(Boolean) : [];
    if (!list.length && !archive) return;
    setUploadBusy(true);
    setIngestErr(null);
    try {
      const job = await startWorkspaceBatchIngest(workspaceMeta.id, list, archive);
      const jid = String(job?.job_id || "").trim();
      if (jid) {
        setIngestJob(job);
        setIngestJobId(jid);
        setPersistedIngestJobId(workspaceMeta.id, jid);
      }
    } catch (err) {
      setIngestErr(formatResearchApiError(err));
    } finally {
      setUploadBusy(false);
    }
  }

  const handleRemovePaper = useCallback(
    async (workId) => {
      const wid = String(workId || "").trim();
      const wsv = String(workspaceMeta.id || "").trim();
      if (!wid || !wsv) return;
      const ok = await confirm({
        title: t("workspace.removePaper.confirmTitle"),
        body: t("workspace.removePaper.confirmBody"),
        variant: "danger",
        confirmLabel: t("workspace.removePaper.confirm"),
        cancelLabel: t("chat.clear.cancel"),
      });
      if (!ok) return;
      try {
        const data = await removeWorkFromWorkspace(wsv, wid);
        const ws = data?.workspace;
        const status = String(data?.removal_status || "detached_only");
        if (ws) setWorkspaceMeta(ws);
        else await refreshWorkspaceMeta();

        const nextList = Array.isArray(ws?.work_ids) ? ws.work_ids : [];
        const focusBefore = String(selectedWorkId || workIdFromUrl || "").trim();
        const p = new URLSearchParams();
        p.set("workspace_id", wsv);
        if (nextList.length === 1) {
          p.set("work_id", String(nextList[0]));
        } else if (nextList.length > 1) {
          const keep =
            focusBefore && focusBefore !== wid && nextList.includes(focusBefore)
              ? focusBefore
              : String(nextList[0] || "");
          if (keep) p.set("work_id", keep);
        }
        setSearchParams(p, { replace: true });

        const toastKey =
          status === "purged"
            ? "workspace.removePaper.toastPurged"
            : status === "purge_blocked_by_incoming_cites"
              ? "workspace.removePaper.toastPurgeBlocked"
              : "workspace.removePaper.toastDetached";
        showToast(t(toastKey));
      } catch (err) {
        showToast(formatResearchApiError(err));
      }
    },
    [
      workspaceMeta.id,
      confirm,
      showToast,
      t,
      setWorkspaceMeta,
      refreshWorkspaceMeta,
      setSearchParams,
      selectedWorkId,
      workIdFromUrl,
    ],
  );

  const onCardActivate =
    workspaceMeta.id && effectiveWorkIds.length > 1 ? (wid) => setWorkFocusInUrl(wid) : undefined;

  const retryWorkspaceLoad = useCallback(() => {
    setWorkspaceLoadNonce((n) => n + 1);
  }, []);

  return {
    t,
    workspaceMeta,
    workspaceLoading,
    workspaceError,
    workspaceErrorIsServer,
    addWorkInput,
    setAddWorkInput,
    addBusy,
    addErr,
    papers,
    ingestJobId,
    ingestJob,
    ingestErr,
    ingestDedupPanelOpen,
    dismissIngestDedupPanel: () => setIngestDedupPanelOpen(false),
    uploadBusy,
    graphStats,
    summaryOpen,
    setSummaryOpen,
    summaryBusy,
    summaryText,
    ideaOpen,
    setIdeaOpen,
    ideaBusy,
    ideaError,
    ideaResult,
    canUseIdeaAssist,
    effectiveWorkIds,
    selectedWorkId,
    refreshWorkspaceMeta,
    emptyState,
    handleAddWork,
    handleUploadDocument,
    handleUploadBatch,
    onCardActivate,
    handleRemovePaper,
    handleSummarizeWorkspace,
    handleGenerateHypotheses,
    retryWorkspaceLoad,
  };
}
