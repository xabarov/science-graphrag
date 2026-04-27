import React, { useMemo } from "react";
import { useTheme } from "@mui/material/styles";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

import { useI18n } from "../../../i18n/useI18n.js";

export default function CaseGraphExpectationsSnapshotColumn({
  snapshotJson,
  snapshotMetrics,
  snapshotMetricsRoot,
  snapshotGoldFromFile,
}) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const preSmallSx = useMemo(
    () => ({
      whiteSpace: "pre-wrap",
      wordBreak: "break-word",
      border: `1px solid ${tk.border.default}`,
      borderRadius: 2,
      padding: 2,
      maxHeight: 280,
      overflow: "auto",
      background: tk.control.outlinedBg,
      fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
      fontSize: "11px",
    }),
    [tk],
  );

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
      <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem" }}>
        {t("benchmark.caseDialog.loadedSnapshotTitle")}
      </Typography>
      {!snapshotJson ? (
        <Typography sx={{ fontSize: "0.8125rem", color: tk.text.muted }}>
          {t("benchmark.caseDialog.loadSnapshotHint")}
        </Typography>
      ) : (
        <>
          {snapshotJson && !snapshotMetrics ? (
            <Typography sx={{ color: "rgba(255,200,100,0.9)", fontSize: "0.8125rem" }}>
              {t("benchmark.caseDialog.noMetricsSnapshotInFile")}
            </Typography>
          ) : null}
          <Accordion defaultExpanded>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography sx={{ fontWeight: 600 }}>{t("benchmark.caseDialog.metricsFileAccordion")}</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Box component="pre" sx={preSmallSx}>
                {JSON.stringify(snapshotMetricsRoot ?? {}, null, 2)}
              </Box>
            </AccordionDetails>
          </Accordion>
          <Accordion defaultExpanded={false}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography sx={{ fontWeight: 600 }}>{t("benchmark.caseDialog.metricsSnapshotAccordion")}</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Box component="pre" sx={preSmallSx}>
                {JSON.stringify(snapshotMetrics ?? {}, null, 2)}
              </Box>
            </AccordionDetails>
          </Accordion>
          <Accordion defaultExpanded={false}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography sx={{ fontWeight: 600 }}>{t("benchmark.caseDialog.goldEmbeddedAccordion")}</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Box component="pre" sx={preSmallSx}>
                {snapshotGoldFromFile != null ? JSON.stringify(snapshotGoldFromFile, null, 2) : "{}"}
              </Box>
            </AccordionDetails>
          </Accordion>
        </>
      )}
    </Box>
  );
}
