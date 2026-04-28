import React from "react";
import { Link, useSearchParams } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import AccountTreeOutlinedIcon from "@mui/icons-material/AccountTreeOutlined";
import MenuBookOutlinedIcon from "@mui/icons-material/MenuBookOutlined";

import { CursorIconAction } from "../../../components/common/index.js";
import ReaderClaimsPanel from "../../../components/work/ReaderClaimsPanel.jsx";
import ReaderWorkBody from "../../../components/work/ReaderWorkBody.jsx";
import { GRAPH_PATH } from "../../../routes/paths.js";
import { buildStandaloneTracePath, readTraceabilityState } from "../../../components/work/traceabilityState.js";
import { useI18n } from "../../../i18n/useI18n.js";

/**
 * @param {{ workId: string }} props
 */
export default function ReaderTab({ workId }) {
  const theme = useTheme();
  const tk = theme.appTokens;
  const { t } = useI18n();
  const [searchParams] = useSearchParams();
  const trace = readTraceabilityState(searchParams);

  if (!workId.trim()) {
    return (
      <Typography sx={{ fontSize: "0.8125rem", color: tk.text.muted }}>{t("wsTab.reader.pickWork")}</Typography>
    );
  }

  return (
    <Box>
      <Typography sx={{ color: tk.text.secondary, fontSize: "0.8125rem", mb: 2 }}>{t("wsTab.reader.liveLine")}</Typography>
      <Box sx={{ mb: 1.5, display: "flex", flexWrap: "wrap", gap: 0.75, alignItems: "center" }}>
        <CursorIconAction component={Link} to={`/reader?work_id=${encodeURIComponent(workId)}`} title={t("wsTab.reader.openStandalone")}>
          <MenuBookOutlinedIcon sx={{ fontSize: "1.05rem" }} />
        </CursorIconAction>
        <CursorIconAction
          component={Link}
          to={buildStandaloneTracePath(GRAPH_PATH, workId, {
            workspaceId: trace.workspaceId,
            section: trace.section,
            citation: trace.citation,
          })}
          title={t("wsTab.reader.jumpGraph")}
        >
          <AccountTreeOutlinedIcon sx={{ fontSize: "1.05rem" }} />
        </CursorIconAction>
      </Box>
      <ReaderClaimsPanel workId={workId} />
      <ReaderWorkBody
        workId={workId}
        workspaceId={trace.workspaceId}
        focusedFingerprint={trace.chunkFingerprint}
        focusedSection={trace.section}
        citation={trace.citation}
      />
    </Box>
  );
}
