import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { useI18n } from "../../../i18n/useI18n.js";
import CaseGraphExpectationsPanel from "../caseDetail/CaseGraphExpectationsPanel.jsx";

/**
 * @param {{ caseId: string | null, caseDetail: Record<string, unknown> | null, fixtureDetail: Record<string, unknown> | null }} props
 */
export default function GraphCaseInspectorPanel({ caseId, caseDetail, fixtureDetail }) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const goldPayload =
    /** @type {Record<string, unknown> | undefined} */ (caseDetail?.gold)?.payload ||
    /** @type {Record<string, unknown> | undefined} */ (fixtureDetail?.gold);
  const ge = goldPayload?.graph_expectations;
  if (!ge) {
    return (
      <Typography sx={{ fontSize: "0.8125rem", color: tk.text.secondary }}>{t("benchmark.inspector.graph.noExpectations")}</Typography>
    );
  }
  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
      <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem" }}>{t("benchmark.inspector.graph.title")}</Typography>
      <CaseGraphExpectationsPanel
        open
        caseId={caseId || ""}
        family="graph"
        graphSnapshotApiFamily="graph"
        detail={{ gold: goldPayload }}
      />
    </Box>
  );
}
