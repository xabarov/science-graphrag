import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { Link } from "react-router-dom";

import { CursorSmallButton } from "../common/index.js";
import { buildStandaloneChatPath, buildStandaloneEvidencePath } from "./traceabilityState.js";
import { useI18n } from "../../i18n/useI18n.js";

/**
 * @param {{
 *   workId: string,
 *   workspaceId?: string,
 *   traceSummary: string[],
 *   focusedFingerprint?: string,
 *   focusedSection?: string,
 *   citation?: string,
 * }} props
 */
export default function ReaderTraceContextBanner({
  workId,
  workspaceId = "",
  traceSummary,
  focusedFingerprint = "",
  focusedSection = "",
  citation = "",
}) {
  const { t } = useI18n();
  if (!traceSummary.length) return null;

  const traceParams = {
    chunkFingerprint: focusedFingerprint,
    section: focusedSection,
    citation,
  };

  return (
    <Box
      sx={{
        mb: 1.5,
        p: 1.25,
        borderRadius: "6px",
        border: "1px solid rgba(99,102,241,0.2)",
        backgroundColor: "rgba(99,102,241,0.08)",
      }}
    >
      <Typography sx={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)", mb: 0.5 }}>{t("readerBody.focusedContext")}</Typography>
      <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.8)" }}>
        {t("readerBody.openedFrom", { summary: traceSummary.join(" · ") })}
      </Typography>
      <Box sx={{ mt: 1, display: "flex", flexWrap: "wrap", gap: 1 }}>
        <CursorSmallButton
          component={Link}
          to={buildStandaloneChatPath(workId, { workspaceId, ...traceParams })}
          sx={{ textDecoration: "none" }}
        >
          {t("readerBody.returnAsk")}
        </CursorSmallButton>
        <CursorSmallButton
          component={Link}
          to={buildStandaloneEvidencePath(workId, { workspaceId, ...traceParams })}
          sx={{ textDecoration: "none" }}
        >
          {t("readerBody.openEvidence")}
        </CursorSmallButton>
      </Box>
    </Box>
  );
}
