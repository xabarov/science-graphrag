import React, { useCallback, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import AskPanel from "../../../components/work/AskPanel.jsx";
import { sessionExistsInScope } from "../../../components/work/askSessionState.js";
import { describeTraceabilityState, readTraceabilityState } from "../../../components/work/traceabilityState.js";

/**
 * @param {{ workId: string }} props
 */
export default function AskTab({ workId }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const trace = readTraceabilityState(searchParams);
  const traceSummary = describeTraceabilityState(trace);
  const askSessionUrl = (searchParams.get("ask_session") || "").trim();
  const sessionScopeKey = `workspace:${workId.trim()}`;

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
    if (!workId.trim() || !askSessionUrl) return;
    if (!sessionExistsInScope(sessionScopeKey, askSessionUrl)) {
      const p = new URLSearchParams(searchParams);
      p.delete("ask_session");
      setSearchParams(p, { replace: true });
    }
  }, [askSessionUrl, workId, sessionScopeKey, searchParams, setSearchParams]);

  if (!workId.trim()) {
    return (
      <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>
        Pick a work from Corpus to scope questions to that work.
      </Typography>
    );
  }

  return (
    <Box>
      {traceSummary.length > 0 ? (
        <Box
          sx={{
            mb: 2,
            p: 1.25,
            borderRadius: "6px",
            border: "1px solid rgba(255,255,255,0.08)",
            backgroundColor: "#1a1a1a",
          }}
        >
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)" }}>Research context</Typography>
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.8)", mt: 0.5 }}>
            Continue the current question flow from {traceSummary.join(" · ")}.
          </Typography>
        </Box>
      ) : null}
      <AskPanel
        scopedWorkId={workId}
        showPageChrome={false}
        workspaceWorkId={workId}
        urlSessionId={askSessionUrl}
        onUrlSessionIdChange={onAskSessionUrlChange}
      />
    </Box>
  );
}
