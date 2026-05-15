import { useCallback } from "react";

import { formatResearchApiError } from "../../services/researchApi.js";
import {
  setActiveWorkspaceId,
  getWorkspace,
  createWorkspace,
  addWorkToWorkspace,
  removeWorkFromWorkspace,
  startWorkspaceDocumentIngest,
  startWorkspaceBatchIngest,
} from "../../utils/workspaceStore.js";
import { setPersistedIngestJobId } from "./workspaceIngestStorage.js";

/**
 * Workspace CRUD, ingest starts, and URL updates that depend on workspace state.
 */
export function useWorkspacePageWorkspaceMutations({
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
}) {
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
  }, [setEmptyCreateBusy, setEmptyCreateErr, setSearchParams]);

  const handleAddWork = useCallback(
    async (e) => {
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
    },
    [
      addWorkInput,
      workspaceMeta.id,
      setAddBusy,
      setAddErr,
      setAddWorkInput,
      setWorkspaceMeta,
    ],
  );

  const handleUploadDocument = useCallback(
    async (ev) => {
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
    },
    [workspaceMeta.id, setIngestErr, setIngestJob, setIngestJobId, setUploadBusy],
  );

  const handleUploadBatch = useCallback(
    async (files, archive = null) => {
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
    },
    [workspaceMeta.id, setIngestErr, setIngestJob, setIngestJobId, setUploadBusy],
  );

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

  return {
    handleEmptyCreateWorkspace,
    handleAddWork,
    handleUploadDocument,
    handleUploadBatch,
    handleRemovePaper,
  };
}
