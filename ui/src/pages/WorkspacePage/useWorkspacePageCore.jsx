import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Box from "@mui/material/Box";
import Alert from "@mui/material/Alert";

import FolderOpenOutlinedIcon from "@mui/icons-material/FolderOpenOutlined";
import HomeOutlinedIcon from "@mui/icons-material/HomeOutlined";

import { CursorIconAction, CursorPrimaryButton } from "../../components/common/index.js";
import { formatResearchApiError, postAgentQuery, postIdeaAssist } from "../../services/researchApi.js";
import {
  getActiveWorkspaceId,
  setActiveWorkspaceId,
  listWorkspaces,
  getWorkspace,
  createWorkspace,
  addWorkToWorkspace,
  startWorkspaceDocumentIngest,
  startWorkspaceBatchIngest,
  getWorkspaceGraphStats,
  getWorkspaceAuthorDedupConflicts,
  getWorkspaceSmartDedupConflicts,
  listEntityDedupConflicts,
} from "../../utils/workspaceStore.js";
import { isAdminModeEnabled } from "../../components/layout/adminVisibility.js";
import { persistWorkId, resolveSelectedWorkId } from "./utils/workContext.js";
import { useI18n } from "../../i18n/I18nContext.jsx";
import useJobStream from "../../hooks/useJobStream.js";
import { useWorkspacePapersModel } from "./useWorkspacePapersModel.js";

const INGEST_JOB_STORAGE_PREFIX = "science-graphrag:workspaceIngestJob:";

export function useWorkspacePageCore() {
  const { t } = useI18n();
  const [searchParams, setSearchParams] = useSearchParams();
  const workspaceIdFromUrl = (searchParams.get("workspace_id") || "").trim();
  const workIdFromUrl = (searchParams.get("work_id") || "").trim();

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
  const [summaryOpen, setSummaryOpen] = useState(false);
  const [summaryBusy, setSummaryBusy] = useState(false);
  const [summaryText, setSummaryText] = useState("");
  const [ideaOpen, setIdeaOpen] = useState(false);
  const [ideaBusy, setIdeaBusy] = useState(false);
  const [ideaError, setIdeaError] = useState("");
  const [ideaResult, setIdeaResult] = useState({ hypotheses: [], contradictions: [], toolTrace: [] });
  const canUseIdeaAssist = useMemo(() => isAdminModeEnabled(), []);

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

  const setPersistedIngestJobId = useCallback((workspaceId, jobId) => {
    const ws = String(workspaceId || "").trim();
    if (!ws) return;
    const key = `${INGEST_JOB_STORAGE_PREFIX}${ws}`;
    try {
      const jid = String(jobId || "").trim();
      if (jid) window.sessionStorage.setItem(key, jid);
      else window.sessionStorage.removeItem(key);
    } catch {
      /* ignore */
    }
  }, []);

  const readPersistedIngestJobId = useCallback((workspaceId) => {
    const ws = String(workspaceId || "").trim();
    if (!ws) return "";
    try {
      return String(window.sessionStorage.getItem(`${INGEST_JOB_STORAGE_PREFIX}${ws}`) || "").trim();
    } catch {
      return "";
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setWorkspaceLoading(true);
      setWorkspaceError(null);
      setWorkspaceErrorIsServer(false);
      try {
        const list = await listWorkspaces();
        if (cancelled) return;
        let activeId = workspaceIdFromUrl || getActiveWorkspaceId();
        if (!activeId && list.length) activeId = list[0].id;
        if (!activeId) {
          setWorkspaceMeta({ id: "", name: "", work_ids: [] });
          return;
        }
        setActiveWorkspaceId(activeId);
        const ws = await getWorkspace(activeId);
        if (cancelled) return;
        if (!ws) {
          setWorkspaceError(t("workspace.err.notFound"));
          setWorkspaceMeta({ id: "", name: "", work_ids: [] });
          return;
        }
        setWorkspaceMeta(ws);
        const restoredJobId = readPersistedIngestJobId(ws.id);
        if (restoredJobId) setIngestJobId(restoredJobId);
        const nextParams = new URLSearchParams();
        nextParams.set("workspace_id", ws.id);
        const ids = Array.isArray(ws.work_ids) ? ws.work_ids : [];
        if (ids.length === 1) {
          nextParams.set("work_id", ids[0]);
        } else if (workIdFromUrl && ids.includes(workIdFromUrl)) {
          nextParams.set("work_id", workIdFromUrl);
        }
        setSearchParams(nextParams, { replace: true });
      } catch (e) {
        if (!cancelled) {
          const status = e?.response?.status;
          const server = typeof status === "number" && status >= 500;
          setWorkspaceErrorIsServer(server);
          const base = formatResearchApiError(e);
          const suffix = server ? ` ${t("workspace.err.serverHintInline")}` : "";
          setWorkspaceError(`${base}${suffix}`.trim());
        }
      } finally {
        if (!cancelled) setWorkspaceLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [workspaceIdFromUrl, workIdFromUrl, workspaceLoadNonce, setSearchParams, t, readPersistedIngestJobId]);

  const retryWorkspaceLoad = useCallback(() => {
    setWorkspaceLoadNonce((n) => n + 1);
  }, []);

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
  }, [workspaceMeta.id]);

  useEffect(() => {
    const id = String(workspaceMeta.id || "").trim();
    if (!id) {
      setIngestDedupPanelOpen(false);
      return undefined;
    }
    let cancelled = false;
    (async () => {
      try {
        const entityTypes = ["institution", "venue", "method", "dataset"];
        const [wdata, adata, ...edatas] = await Promise.all([
          getWorkspaceSmartDedupConflicts(id, { status: "pending", origin: "ingest", limit: 1 }),
          getWorkspaceAuthorDedupConflicts(id, { status: "pending", origin: "ingest", limit: 1 }),
          ...entityTypes.map((entityType) =>
            listEntityDedupConflicts({
              entityType,
              workspaceId: id,
              origin: "ingest",
              status: "pending",
              limit: 1,
            }),
          ),
        ]);
        const hasWork = Array.isArray(wdata?.items) && wdata.items.length > 0;
        const hasAuthor = Array.isArray(adata?.items) && adata.items.length > 0;
        const hasEntity = edatas.some((d) => Array.isArray(d?.items) && d.items.length > 0);
        if (!cancelled && (hasWork || hasAuthor || hasEntity)) {
          setIngestDedupPanelOpen(true);
        }
      } catch {
        /* ignore */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [workspaceMeta.id]);

  const effectiveWorkIds = useMemo(() => {
    const fromWs = Array.isArray(workspaceMeta.work_ids) ? workspaceMeta.work_ids : [];
    if (fromWs.length) return fromWs;
    return [];
  }, [workspaceMeta.work_ids]);

  const selectedWorkId = useMemo(
    () => resolveSelectedWorkId({ workIds: effectiveWorkIds, workIdFromUrl }),
    [effectiveWorkIds, workIdFromUrl],
  );

  const { papers } = useWorkspacePapersModel({
    workspaceId: workspaceMeta.id || "",
    effectiveWorkIds,
  });

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
      [refreshWorkspaceMeta, setPersistedIngestJobId, workspaceMeta.id],
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
      <Box sx={{ maxWidth: 560, mt: 2 }}>
        <Alert severity="info" sx={{ fontSize: "0.8125rem", mb: 2, backgroundColor: "rgba(99,102,241,0.08)", color: "rgba(255,255,255,0.85)" }}>
          {t("workspace.empty.alert")}
        </Alert>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, alignItems: "center", mb: emptyCreateErr ? 1 : 0 }}>
          <CursorPrimaryButton type="button" disabled={emptyCreateBusy} onClick={() => void handleEmptyCreateWorkspace()}>
            {t("workspace.empty.createWorkspace")}
          </CursorPrimaryButton>
          <CursorIconAction component={Link} to="/workspaces" title={t("workspace.empty.workspaces")}>
            <FolderOpenOutlinedIcon sx={{ fontSize: "1.1rem" }} />
          </CursorIconAction>
          <Box component="span" sx={{ display: "inline-flex" }}>
            <CursorIconAction component={Link} to="/home" title={t("workspace.empty.about")}>
              <HomeOutlinedIcon sx={{ fontSize: "1.1rem" }} />
            </CursorIconAction>
          </Box>
        </Box>
        {emptyCreateErr ? (
          <Alert severity="error" sx={{ fontSize: "0.8125rem", mt: 1 }}>
            {emptyCreateErr}
          </Alert>
        ) : null}
      </Box>
    ),
    [t, emptyCreateBusy, emptyCreateErr, handleEmptyCreateWorkspace],
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

  const onCardActivate =
    workspaceMeta.id && effectiveWorkIds.length > 1 ? (wid) => setWorkFocusInUrl(wid) : undefined;

  async function handleSummarizeWorkspace() {
    if (!workspaceMeta.id) return;
    setSummaryBusy(true);
    try {
      const res = await postAgentQuery({
        question: "Briefly summarize this workspace: topics, methods, datasets, and key findings.",
        workspace_id: workspaceMeta.id,
        max_tool_calls: 8,
      });
      setSummaryText(String(res?.data?.answer || ""));
      setSummaryOpen(true);
    } catch (err) {
      setSummaryText(formatResearchApiError(err));
      setSummaryOpen(true);
    } finally {
      setSummaryBusy(false);
    }
  }

  async function handleGenerateHypotheses() {
    if (!workspaceMeta.id || !canUseIdeaAssist) return;
    setIdeaBusy(true);
    setIdeaError("");
    try {
      const res = await postIdeaAssist({
        workspace_id: workspaceMeta.id,
        mode: "both",
        max_candidates: 3,
      });
      const data = res?.data || {};
      setIdeaResult({
        hypotheses: Array.isArray(data.hypotheses) ? data.hypotheses : [],
        contradictions: Array.isArray(data.contradictions) ? data.contradictions : [],
        toolTrace: Array.isArray(data.tool_trace) ? data.tool_trace : [],
      });
      setIdeaOpen(true);
    } catch (err) {
      setIdeaResult({ hypotheses: [], contradictions: [], toolTrace: [] });
      setIdeaError(formatResearchApiError(err));
      setIdeaOpen(true);
    } finally {
      setIdeaBusy(false);
    }
  }

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
    handleSummarizeWorkspace,
    handleGenerateHypotheses,
    retryWorkspaceLoad,
  };
}
