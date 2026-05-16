import React, { useCallback, useEffect, useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Box from "@mui/material/Box";
import HubOutlinedIcon from "@mui/icons-material/HubOutlined";

import { AskPanel } from "../components/work/ask/index.js";
import { useWorkspaceContext } from "../components/layout/useWorkspaceContext.js";
import { useI18n } from "../i18n/useI18n.js";
import { CursorIconAction } from "../components/common/index.js";
import { persistLastChatHref } from "../components/layout/shellNavHref.js";
import { CHAT_PATH } from "../routes/paths.js";

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

  const onAskSessionUrlChange = useCallback(
    (sessionId) => {
      const p = new URLSearchParams(searchParams);
      if (sessionId) p.set("ask_session", sessionId);
      else p.delete("ask_session");
      setSearchParams(p, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  const onUrlWorkIdChange = useCallback(
    (workId) => {
      const p = new URLSearchParams(searchParams);
      const next = String(workId || "").trim();
      if (next) p.set("work_id", next);
      else p.delete("work_id");
      setSearchParams(p, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  useEffect(() => {
    const qs = searchParams.toString();
    const href = qs ? `${CHAT_PATH}?${qs}` : CHAT_PATH;
    persistLastChatHref(href);
  }, [searchParams]);

  /** Keep `workspace_id` in the URL once shell knows it — stabilizes ask scope vs late `activeWorkspaceId`. */
  useEffect(() => {
    const fromUrl = workspaceIdFromUrl.trim();
    const active = (activeWorkspaceId || "").trim();
    if (fromUrl || !active) return;
    const p = new URLSearchParams(searchParams);
    p.set("workspace_id", active);
    setSearchParams(p, { replace: true });
  }, [workspaceIdFromUrl, activeWorkspaceId, searchParams, setSearchParams]);

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
        onUrlWorkIdChange={onUrlWorkIdChange}
        fillAvailableHeight
      />
    </Box>
  );
}
