import React from "react";
import { Link, useSearchParams } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import EvidenceWorkBody from "../../../components/work/EvidenceWorkBody.jsx";
import AccountTreeOutlinedIcon from "@mui/icons-material/AccountTreeOutlined";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import MenuBookOutlinedIcon from "@mui/icons-material/MenuBookOutlined";

import { CursorIconAction } from "../../../components/common/index.js";
import { buildWorkspaceTracePath, readTraceabilityState } from "../../../components/work/traceabilityState.js";
import { useI18n } from "../../../i18n/I18nContext.jsx";

/**
 * @param {{ workId: string }} props
 */
export default function EvidenceTab({ workId }) {
  const { t } = useI18n();
  const [searchParams] = useSearchParams();
  const trace = readTraceabilityState(searchParams);

  if (!workId.trim()) {
    return (
      <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>{t("wsTab.evidence.pickWork")}</Typography>
    );
  }

  return (
    <Box>
      <Typography sx={{ color: "rgba(255,255,255,0.55)", fontSize: "0.8125rem", mb: 2 }}>{t("wsTab.evidence.liveLine")}</Typography>
      <Box sx={{ mb: 1.5, display: "flex", flexWrap: "wrap", gap: 0.75, alignItems: "center" }}>
        <CursorIconAction
          component={Link}
          to={buildWorkspaceTracePath(workId, "reader", {
            chunkFingerprint: trace.chunkFingerprint,
            section: trace.section,
            citation: trace.citation,
          })}
          title={t("wsTab.evidence.jumpReader")}
        >
          <MenuBookOutlinedIcon sx={{ fontSize: "1.05rem" }} />
        </CursorIconAction>
        <CursorIconAction
          component={Link}
          to={buildWorkspaceTracePath(workId, "graph", {
            section: trace.section,
            citation: trace.citation,
          })}
          title={t("wsTab.evidence.jumpGraph")}
        >
          <AccountTreeOutlinedIcon sx={{ fontSize: "1.05rem" }} />
        </CursorIconAction>
        <CursorIconAction
          component={Link}
          to={`/evidence?work_id=${encodeURIComponent(workId)}`}
          title={t("wsTab.evidence.openStandalone")}
        >
          <DescriptionOutlinedIcon sx={{ fontSize: "1.05rem" }} />
        </CursorIconAction>
      </Box>
      <EvidenceWorkBody
        workId={workId}
        highlightedFingerprint={trace.chunkFingerprint}
        highlightedSection={trace.section}
        citation={trace.citation}
      />
    </Box>
  );
}
