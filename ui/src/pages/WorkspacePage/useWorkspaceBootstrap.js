import { useEffect } from "react";

import { formatResearchApiError } from "../../services/researchApi.js";
import {
  getActiveWorkspaceId,
  setActiveWorkspaceId,
  listWorkspaces,
  getWorkspace,
} from "../../utils/workspaceStore.js";
import { readPersistedIngestJobId } from "./workspaceIngestStorage.js";

/**
 * Initial workspace load from URL / persisted selection and URL sync.
 */
export function useWorkspaceBootstrap({
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
}) {
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
  }, [workspaceIdFromUrl, workIdFromUrl, workspaceLoadNonce, setSearchParams, setWorkspaceMeta, setWorkspaceLoading, setWorkspaceError, setWorkspaceErrorIsServer, setIngestJobId, t]);
}
