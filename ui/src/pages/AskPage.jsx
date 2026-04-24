import React, { useCallback, useEffect, useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Box from "@mui/material/Box";

import AskPanel from "../components/work/AskPanel.jsx";
import { deriveAskScopeKey, sessionExistsInScope } from "../components/work/askSessionState.js";
import PageHeader from "../components/layout/PageHeader.jsx";
import { mainShellContentSx } from "../components/layout/mainShellContentSx.js";
import { useWorkspaceContext } from "../components/layout/WorkspaceContext.jsx";
import { useI18n } from "../i18n/I18nContext.jsx";
import { persistWorkId } from "./WorkspacePage/utils/workContext.js";
import { CursorPrimaryButton } from "../components/common/index.js";

/** Standalone Ask entry; workspace tab is the primary UX when a work is selected. */
export default function AskPage() {
  const { t } = useI18n();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialWorkId = searchParams.get("work_id") || "";
  const workspaceIdFromUrl = (searchParams.get("workspace_id") || "").trim();
  const { activeWorkspaceId, getLastWorkspaceHref } = useWorkspaceContext();
  const askSessionUrl = (searchParams.get("ask_session") || "").trim();

  const effectiveWorkspaceId = useMemo(
    () => workspaceIdFromUrl || (activeWorkspaceId || "").trim(),
    [workspaceIdFromUrl, activeWorkspaceId],
  );

  const askSessionScopeKey = useMemo(
    () => deriveAskScopeKey({ locked: false, scopedWorkId: null, workspaceId: effectiveWorkspaceId }),
    [effectiveWorkspaceId],
  );

  const onAskSessionUrlChange = useCallback(
    (sessionId) => {
      const p = new URLSearchParams(searchParams);
      if (sessionId) p.set("ask_session", sessionId);
      else p.delete("ask_session");
      setSearchParams(p, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  useEffect(() => {
    if (initialWorkId.trim()) persistWorkId(initialWorkId);
  }, [initialWorkId]);

  useEffect(() => {
    if (!askSessionUrl) return;
    if (!sessionExistsInScope(askSessionScopeKey, askSessionUrl)) {
      const p = new URLSearchParams(searchParams);
      p.delete("ask_session");
      setSearchParams(p, { replace: true });
    }
  }, [askSessionUrl, askSessionScopeKey, searchParams, setSearchParams]);

  const showEmptyCta = !initialWorkId.trim() && !workspaceIdFromUrl && !activeWorkspaceId;

  return (
    <Box sx={{ p: 2, ...mainShellContentSx }}>
      <PageHeader
        eyebrow={t("askPage.header.eyebrow")}
        title={t("askPage.header.title")}
        description={t("askPage.header.description")}
      />
      {showEmptyCta ? (
        <Box sx={{ mb: 2 }}>
          <CursorPrimaryButton component={Link} to={getLastWorkspaceHref()} sx={{ textDecoration: "none" }}>
            {t("askPage.empty.openLastWorkspace")}
          </CursorPrimaryButton>
        </Box>
      ) : null}
      <AskPanel
        initialWorkId={initialWorkId}
        workspaceId={effectiveWorkspaceId}
        showPageChrome={false}
        urlSessionId={askSessionUrl}
        onUrlSessionIdChange={onAskSessionUrlChange}
      />
    </Box>
  );
}
