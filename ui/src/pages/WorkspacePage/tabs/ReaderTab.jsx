import React from "react";
import { Link, useSearchParams } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import ReaderWorkBody from "../../../components/work/ReaderWorkBody.jsx";
import { CursorSmallButton } from "../../../components/common/index.js";
import { buildWorkspaceTracePath, readTraceabilityState } from "../../../components/work/traceabilityState.js";
import { useI18n } from "../../../i18n/I18nContext.jsx";

/**
 * @param {{ workId: string }} props
 */
export default function ReaderTab({ workId }) {
  const { t } = useI18n();
  const [searchParams] = useSearchParams();
  const trace = readTraceabilityState(searchParams);

  if (!workId.trim()) {
    return (
      <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>{t("wsTab.reader.pickWork")}</Typography>
    );
  }

  return (
    <Box>
      <Typography sx={{ color: "rgba(255,255,255,0.55)", fontSize: "0.8125rem", mb: 2 }}>{t("wsTab.reader.liveLine")}</Typography>
      <Box sx={{ mb: 1.5, display: "flex", flexWrap: "wrap", gap: 1, alignItems: "center" }}>
        <CursorSmallButton component={Link} to={`/reader?work_id=${encodeURIComponent(workId)}`} sx={{ textDecoration: "none" }}>
          {t("wsTab.reader.openStandalone")}
        </CursorSmallButton>
        <CursorSmallButton
          component={Link}
          to={buildWorkspaceTracePath(workId, "graph", {
            section: trace.section,
            citation: trace.citation,
          })}
          sx={{ textDecoration: "none" }}
        >
          {t("wsTab.reader.jumpGraph")}
        </CursorSmallButton>
      </Box>
      <ReaderWorkBody
        workId={workId}
        focusedFingerprint={trace.chunkFingerprint}
        focusedSection={trace.section}
        citation={trace.citation}
      />
    </Box>
  );
}
