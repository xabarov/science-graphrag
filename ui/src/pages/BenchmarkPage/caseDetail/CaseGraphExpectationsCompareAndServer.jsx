import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

import { useI18n } from "../../../i18n/I18nContext.jsx";

const preSideBySideSx = {
  whiteSpace: "pre-wrap",
  wordBreak: "break-word",
  border: "1px solid rgba(255,255,255,0.08)",
  borderRadius: 2,
  padding: 1.5,
  maxHeight: 320,
  overflow: "auto",
  background: "rgba(255,255,255,0.02)",
  fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
  fontSize: "11px",
  margin: 0,
};

export default function CaseGraphExpectationsCompareAndServer({
  snapshotJson,
  graphExpectationsJson,
  snapshotGoldFromFile,
  graphCompare,
  serverPreviewError,
  serverPreview,
}) {
  const { t } = useI18n();

  return (
    <>
      {snapshotJson && graphExpectationsJson ? (
        <Accordion defaultExpanded={false}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem" }}>
              {t("benchmark.caseDialog.sideBySideTitle")}
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: { xs: "1fr", md: "minmax(0,1fr) minmax(0,1fr)" },
                gap: 1.5,
                alignItems: "stretch",
              }}
            >
              <Box>
                <Typography sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.5)", mb: 0.5 }}>
                  {t("benchmark.caseDialog.caseGoldLabel")}
                </Typography>
                <Box component="pre" sx={preSideBySideSx}>
                  {graphExpectationsJson}
                </Box>
              </Box>
              <Box>
                <Typography sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.5)", mb: 0.5 }}>
                  {t("benchmark.caseDialog.snapshotEmbeddedGoldLabel")}
                </Typography>
                <Box component="pre" sx={preSideBySideSx}>
                  {snapshotGoldFromFile != null
                    ? JSON.stringify(snapshotGoldFromFile, null, 2)
                    : t("benchmark.caseDialog.snapshotNoGoldPlaceholder")}
                </Box>
              </Box>
            </Box>
          </AccordionDetails>
        </Accordion>
      ) : null}

      {graphCompare.arxivNotes.length ? (
        <Box>
          {graphCompare.arxivNotes.map((line, idx) => (
            <Typography key={idx} sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.65)", mb: 0.5 }}>
              {line}
            </Typography>
          ))}
        </Box>
      ) : null}

      {graphCompare.rows.length ? (
        <Box sx={{ border: "1px solid rgba(255,255,255,0.08)", borderRadius: 1.5, overflow: "hidden" }}>
          <Typography sx={{ px: 1.5, py: 1, fontWeight: 600, fontSize: "0.8125rem" }}>
            {t("benchmark.caseDialog.snapshotVsExpectationsTitle")}
          </Typography>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>{t("benchmark.caseDialog.tableField")}</TableCell>
                <TableCell>{t("benchmark.caseDialog.tableSnapshot")}</TableCell>
                <TableCell>{t("benchmark.caseDialog.tableExpected")}</TableCell>
                <TableCell>{t("benchmark.caseDialog.tableOk")}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {graphCompare.rows.map((row) => (
                <TableRow key={row.field}>
                  <TableCell>{row.field}</TableCell>
                  <TableCell>{row.snapshot}</TableCell>
                  <TableCell>{row.expected}</TableCell>
                  <TableCell sx={{ color: row.ok ? "rgba(129,140,248,0.95)" : "rgba(239,68,68,0.9)" }}>
                    {row.ok ? t("benchmark.caseDialog.tableOkYes") : t("benchmark.caseDialog.tableOkNo")}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>
      ) : null}

      {serverPreviewError ? (
        <Typography sx={{ color: "rgba(239,68,68,0.9)", fontSize: "0.8125rem" }} role="alert">
          {serverPreviewError}
        </Typography>
      ) : null}

      {serverPreview?.arxiv_notes?.length ? (
        <Box>
          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mb: 0.5 }}>
            {t("benchmark.caseDialog.serverPreviewArxivNotes")}
          </Typography>
          {serverPreview.arxiv_notes.map((line, idx) => (
            <Typography key={idx} sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.65)", mb: 0.5 }}>
              {line}
            </Typography>
          ))}
        </Box>
      ) : null}

      {serverPreview?.rows?.length ? (
        <Box sx={{ border: "1px solid rgba(99,102,241,0.25)", borderRadius: 1.5, overflow: "hidden" }}>
          <Typography sx={{ px: 1.5, py: 1, fontWeight: 600, fontSize: "0.8125rem" }}>
            {t("benchmark.caseDialog.serverPreviewRangeChecks")}
          </Typography>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>{t("benchmark.caseDialog.tableField")}</TableCell>
                <TableCell>{t("benchmark.caseDialog.tableSnapshot")}</TableCell>
                <TableCell>{t("benchmark.caseDialog.tableExpected")}</TableCell>
                <TableCell>{t("benchmark.caseDialog.tableOk")}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {serverPreview.rows.map((row) => (
                <TableRow key={`srv-${row.field}`}>
                  <TableCell>{row.field}</TableCell>
                  <TableCell>{row.snapshot}</TableCell>
                  <TableCell>{row.expected}</TableCell>
                  <TableCell sx={{ color: row.ok ? "rgba(129,140,248,0.95)" : "rgba(239,68,68,0.9)" }}>
                    {row.ok ? t("benchmark.caseDialog.tableOkYes") : t("benchmark.caseDialog.tableOkNo")}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>
      ) : null}
    </>
  );
}
