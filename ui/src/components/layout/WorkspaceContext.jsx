import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";

import { getActiveWorkspaceId, getWorkspace, setActiveWorkspaceId } from "../../utils/workspaceStore.js";

/**
 * @typedef {{ id: string, name?: string, work_ids?: string[] } | null} WorkspaceMeta
 */

/** @type {React.Context<null | { activeWorkspaceId: string | null, activeWorkspaceMeta: WorkspaceMeta, setActiveWorkspace: (id: string) => void, getLastWorkspaceHref: () => string }>} */
const WorkspaceContext = createContext(null);

export function WorkspaceContextProvider({ children }) {
  const location = useLocation();

  const workspaceIdFromUrl = useMemo(() => {
    const sp = new URLSearchParams((location.search && location.search.replace(/^\?/, "")) || "");
    return (sp.get("workspace_id") || "").trim();
  }, [location.search]);

  useEffect(() => {
    if (workspaceIdFromUrl) setActiveWorkspaceId(workspaceIdFromUrl);
  }, [workspaceIdFromUrl]);

  const resolvedId = useMemo(() => workspaceIdFromUrl || getActiveWorkspaceId() || "", [workspaceIdFromUrl]);

  const [activeWorkspaceMeta, setActiveWorkspaceMeta] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const id = resolvedId;
    if (!id) {
      queueMicrotask(() => {
        if (!cancelled) setActiveWorkspaceMeta(null);
      });
      return () => {
        cancelled = true;
      };
    }
    (async () => {
      try {
        const ws = await getWorkspace(id);
        if (cancelled) return;
        if (ws) setActiveWorkspaceMeta(ws);
        else setActiveWorkspaceMeta({ id, name: "", work_ids: [] });
      } catch {
        if (!cancelled) setActiveWorkspaceMeta({ id, name: id, work_ids: [] });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [resolvedId]);

  const setActiveWorkspace = useCallback((id) => {
    const v = String(id || "").trim();
    setActiveWorkspaceId(v);
    if (!v) setActiveWorkspaceMeta(null);
  }, []);

  const getLastWorkspaceHref = useCallback(() => {
    const id = getActiveWorkspaceId() || resolvedId;
    return id ? `/workspace?workspace_id=${encodeURIComponent(id)}` : "/workspaces";
  }, [resolvedId]);

  const value = useMemo(
    () => ({
      activeWorkspaceId: resolvedId ? resolvedId : null,
      activeWorkspaceMeta,
      setActiveWorkspace,
      getLastWorkspaceHref,
    }),
    [resolvedId, activeWorkspaceMeta, setActiveWorkspace, getLastWorkspaceHref],
  );

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspaceContext() {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) {
    throw new Error("useWorkspaceContext must be used within WorkspaceContextProvider");
  }
  return ctx;
}
