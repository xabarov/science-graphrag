import React, { useCallback, useEffect, useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Box from "@mui/material/Box";
import HubOutlinedIcon from "@mui/icons-material/HubOutlined";

import AskPanel from "../components/work/AskPanel.jsx";
import { deriveAskScopeKey, sessionExistsInScope } from "../components/work/askSessionState.js";
import { useWorkspaceContext } from "../components/layout/WorkspaceContext.jsx";
import { useI18n } from "../i18n/I18nContext.jsx";
import { persistWorkId } from "./WorkspacePage/utils/workContext.js";
import { CursorIconAction } from "../components/common/index.js";

/** Standalone chat entry — full-height GPT-like layout. */
export default function ChatPage() {
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
    <Box
      sx={{
        flex: 1,
        minHeight: 0,
        width: "100%",
        maxWidth: "100%",
        boxSizing: "border-box",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        px: 2,
        pt: 1,
      }}
    >
      {showEmptyCta ? (
        <Box sx={{ mb: 1, flexShrink: 0 }}>
          <CursorIconAction component={Link} to={getLastWorkspaceHref()} title={t("chatPage.empty.openLastWorkspace")}>
            <HubOutlinedIcon sx={{ fontSize: "1.15rem" }} />
          </CursorIconAction>
        </Box>
      ) : null}
      <AskPanel
        initialWorkId={initialWorkId}
        workspaceId={effectiveWorkspaceId}
        showPageChrome={false}
        urlSessionId={askSessionUrl}
        onUrlSessionIdChange={onAskSessionUrlChange}
        fillAvailableHeight
      />
    </Box>
  );
}
