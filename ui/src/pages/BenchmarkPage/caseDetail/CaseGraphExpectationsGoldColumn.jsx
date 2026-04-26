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

import { useI18n } from "../../../i18n/useI18n.js";

export default function CaseGraphExpectationsGoldColumn({
  graphExpectations,
  graphExpectationsJson,
  expectationRangeRows,
}) {
  const { t } = useI18n();

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
      <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem" }}>
        {t("benchmark.caseDialog.goldGraphExpectationsTitle")}
      </Typography>
      {expectationRangeRows.length ? (
        <Box sx={{ border: "1px solid rgba(255,255,255,0.08)", borderRadius: 1.5, overflow: "hidden" }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>{t("benchmark.caseDialog.tableConstraint")}</TableCell>
                <TableCell>{t("benchmark.caseDialog.tableMin")}</TableCell>
                <TableCell>{t("benchmark.caseDialog.tableMax")}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {expectationRangeRows.map((row) => (
                <TableRow key={row.label}>
                  <TableCell sx={{ color: "rgba(255,255,255,0.75)" }}>{row.label}</TableCell>
                  <TableCell>{String(row.low)}</TableCell>
                  <TableCell>{String(row.high)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>
      ) : null}

      {graphExpectations?.max_duplicate_work_fingerprints != null ? (
        <Typography sx={{ fontSize: "0.8125rem" }}>
          <strong>{t("benchmark.caseDialog.maxDupFingerprints")}</strong>{" "}
          {String(graphExpectations.max_duplicate_work_fingerprints)}
          {graphExpectations.max_work_dedup_violations != null
            ? ` | ${t("benchmark.caseDialog.maxWorkDedupViolations")} ${String(graphExpectations.max_work_dedup_violations)}`
            : ""}
        </Typography>
      ) : null}

      {Array.isArray(graphExpectations?.expected_cited_arxiv_ids) ? (
        <Box>
          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mb: 0.5 }}>
            {t("benchmark.caseDialog.expectedCitedArxivIds", {
              count: graphExpectations.expected_cited_arxiv_ids.length,
            })}
          </Typography>
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.55)", wordBreak: "break-word" }}>
            {graphExpectations.expected_cited_arxiv_ids.join(", ")}
          </Typography>
        </Box>
      ) : null}

      <Accordion defaultExpanded={false}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography sx={{ fontWeight: 600 }}>{t("benchmark.caseDialog.rawGraphExpectationsJson")}</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Box
            component="pre"
            sx={{
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: 2,
              padding: 2,
              maxHeight: 320,
              overflow: "auto",
              background: "rgba(255,255,255,0.02)",
              fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
              fontSize: "12px",
            }}
          >
            {graphExpectationsJson}
          </Box>
        </AccordionDetails>
      </Accordion>
    </Box>
  );
}
