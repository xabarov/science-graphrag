import { useCallback, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useTheme } from "@mui/material/styles";

import { useFeedback } from "../../components/feedback/index.js";
import { getWorkspace } from "../../utils/workspaceStore.js";
import { isAdminModeEnabled } from "../../components/layout/adminVisibility.js";
import { useI18n } from "../../i18n/useI18n.js";
import { useWorkspacePapersModel } from "./useWorkspacePapersModel.js";
import { useWorkspaceIdeaAssist } from "./useWorkspaceIdeaAssist.js";
import { useWorkspaceLegacyRedirect } from "./useWorkspaceLegacyRedirect.js";
import { useWorkspaceSummary } from "./useWorkspaceSummary.js";
import { useWorkspaceBootstrap } from "./useWorkspaceBootstrap.js";
import { useIngestDedupAutoOpen } from "./useIngestDedupAutoOpen.js";
import WorkspacePageEmptyState from "./WorkspacePageEmptyState.jsx";
import { useWorkspaceGraphStats } from "./useWorkspaceGraphStats.js";
import { useWorkspaceIngestJobStream } from "./useWorkspaceIngestJobStream.js";
import { useWorkspacePageWorkSelection } from "./useWorkspacePageWorkSelection.js";
import { useWorkspacePageWorkspaceMutations } from "./useWorkspacePageWorkspaceMutations.js";

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

  const graphStats = useWorkspaceGraphStats(workspaceMeta.id, workspaceMeta.work_ids);

  useWorkspaceIngestJobStream({
    workspaceId: workspaceMeta.id,
    ingestJobId,
    setIngestJob,
    setIngestJobId,
    setIngestDedupPanelOpen,
    refreshWorkspaceMeta,
    setIngestErr,
  });

  useIngestDedupAutoOpen(workspaceMeta.id, setIngestDedupPanelOpen);

  const { effectiveWorkIds, selectedWorkId, onCardActivate } = useWorkspacePageWorkSelection({
    workspaceMeta,
    workIdFromUrl,
    setSearchParams,
  });

  const { papers } = useWorkspacePapersModel({ effectiveWorkIds });

  const {
    handleEmptyCreateWorkspace,
    handleAddWork,
    handleUploadDocument,
    handleUploadBatch,
    handleRemovePaper,
  } = useWorkspacePageWorkspaceMutations({
    workspaceMeta,
    setWorkspaceMeta,
    setEmptyCreateBusy,
    setEmptyCreateErr,
    setSearchParams,
    addWorkInput,
    setAddWorkInput,
    setAddBusy,
    setAddErr,
    setIngestJob,
    setIngestJobId,
    setIngestErr,
    setUploadBusy,
    confirm,
    showToast,
    t,
    refreshWorkspaceMeta,
    selectedWorkId,
    workIdFromUrl,
  });

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
