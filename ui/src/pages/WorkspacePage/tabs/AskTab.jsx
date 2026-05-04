import React, { useCallback, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import AskPanel from "../../../components/work/ask/AskPanel.jsx";
import { sessionExistsInScope } from "../../../components/work/ask/askSessionState.js";
import {
  describeTraceabilityState,
  readTraceabilityState,
} from "../../../components/work/traceability/traceabilityState.js";
import { useI18n } from "../../../i18n/useI18n.js";

/**
 * @param {{ workId: string }} props
 */
export default function AskTab({ workId }) {
  const theme = useTheme();
  const tk = theme.appTokens;
  const { t } = useI18n();
  const [searchParams, setSearchParams] = useSearchParams();
  const trace = readTraceabilityState(searchParams);
  const workspaceIdFromUrl = (searchParams.get("workspace_id") || "").trim();
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
      <Typography sx={{ fontSize: "0.8125rem", color: tk.text.muted }}>{t("wsTab.ask.pickWork")}</Typography>
    );
  }

  return (
    <Box>
      {traceSummary.length > 0 ? (
        <Box
          sx={{
            mb: 1.25,
            p: 1.25,
            borderRadius: "6px",
            border: `1px solid ${tk.border.default}`,
            backgroundColor: tk.surface.panel,
          }}
        >
          <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted }}>{t("wsTab.ask.researchContext")}</Typography>
          <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary, mt: 0.5 }}>
            {t("wsTab.ask.contextLine", { summary: traceSummary.join(" · ") })}
          </Typography>
        </Box>
      ) : null}
      <AskPanel
        scopedWorkId={workId}
        showPageChrome={false}
        workspaceWorkId={workId}
        workspaceId={workspaceIdFromUrl}
        urlSessionId={askSessionUrl}
        onUrlSessionIdChange={onAskSessionUrlChange}
      />
    </Box>
  );
}
