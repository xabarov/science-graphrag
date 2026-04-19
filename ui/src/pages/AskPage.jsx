import React, { useCallback, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import Box from "@mui/material/Box";

import AskPanel from "../components/work/AskPanel.jsx";
import { sessionExistsInScope } from "../components/work/askSessionState.js";
import PageHeader from "../components/layout/PageHeader.jsx";
import { mainShellContentSx } from "../components/layout/mainShellContentSx.js";
import { persistWorkId } from "./WorkspacePage/utils/workContext.js";

/** Standalone Ask entry; workspace tab is the primary UX when a work is selected. */
export default function AskPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialWorkId = searchParams.get("work_id") || "";
  const askSessionUrl = (searchParams.get("ask_session") || "").trim();

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
    if (!sessionExistsInScope("standalone", askSessionUrl)) {
      const p = new URLSearchParams(searchParams);
      p.delete("ask_session");
      setSearchParams(p, { replace: true });
    }
  }, [askSessionUrl, searchParams, setSearchParams]);

  return (
    <Box sx={{ p: 2, ...mainShellContentSx }}>
      <PageHeader
        eyebrow="Ask"
        title="Questions"
        description="Paper-scoped or global queries. Pick a paper from Workspaces / Workspace, then set work_id below or in the URL."
      />
      <AskPanel
        initialWorkId={initialWorkId}
        showPageChrome={false}
        urlSessionId={askSessionUrl}
        onUrlSessionIdChange={onAskSessionUrlChange}
      />
    </Box>
  );
}
