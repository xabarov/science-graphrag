import React, { useState } from "react";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Box from "@mui/material/Box";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";

import { formatComparisonCellValue } from "./benchmarkCaseInspectorFormatting.js";
import BenchmarkCaseInspectorJsonBlock from "./BenchmarkCaseInspectorJsonBlock.jsx";

/**
 * Raw payload accordion: article, gold, prediction, metrics, diff table, diagnostics.
 *
 * @param {{
 *   tk: import("@mui/material/styles").Theme["appTokens"],
 *   caseDetail: Record<string, unknown>,
 *   comparisonRows: Record<string, unknown>[],
 *   t: (key: string, vars?: Record<string, string | number>) => string,
 * }} props
 */
export default function BenchmarkCaseInspectorRawAccordion({ tk, caseDetail, comparisonRows, t }) {
  const [rawOpen, setRawOpen] = useState(false);

  return (
    <Accordion expanded={rawOpen} onChange={(_, exp) => setRawOpen(exp)}>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem" }}>{t("benchmark.inspector.raw.toggle")}</Typography>
      </AccordionSummary>
      <AccordionDetails>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
          <Accordion disableGutters elevation={0} sx={{ border: `1px solid ${tk.border.default}`, borderRadius: 1, "&:before": { display: "none" } }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography sx={{ fontSize: "0.8125rem" }}>{t("benchmark.workbench.sourceArticle")}</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Typography component="pre" sx={{ whiteSpace: "pre-wrap", fontSize: "12px", m: 0 }}>
                {String(/** @type {Record<string, unknown>} */ (caseDetail.article)?.raw_markdown || "")}
              </Typography>
            </AccordionDetails>
          </Accordion>
          <Accordion disableGutters elevation={0} sx={{ border: `1px solid ${tk.border.default}`, borderRadius: 1, "&:before": { display: "none" } }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography sx={{ fontSize: "0.8125rem" }}>{t("benchmark.workbench.goldPayload")}</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <BenchmarkCaseInspectorJsonBlock value={/** @type {Record<string, unknown>} */ (caseDetail.gold)?.payload || {}} />
            </AccordionDetails>
          </Accordion>
          <Accordion disableGutters elevation={0} sx={{ border: `1px solid ${tk.border.default}`, borderRadius: 1, "&:before": { display: "none" } }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography sx={{ fontSize: "0.8125rem" }}>{t("benchmark.workbench.prediction")}</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <BenchmarkCaseInspectorJsonBlock value={/** @type {Record<string, unknown>} */ (caseDetail.predicted)?.payload ?? {}} />
            </AccordionDetails>
          </Accordion>
          <Accordion disableGutters elevation={0} sx={{ border: `1px solid ${tk.border.default}`, borderRadius: 1, "&:before": { display: "none" } }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography sx={{ fontSize: "0.8125rem" }}>{t("benchmark.workbench.metrics")}</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <BenchmarkCaseInspectorJsonBlock value={caseDetail.metrics || {}} />
            </AccordionDetails>
          </Accordion>
          <Accordion disableGutters elevation={0} sx={{ border: `1px solid ${tk.border.default}`, borderRadius: 1, "&:before": { display: "none" } }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography sx={{ fontSize: "0.8125rem" }}>{t("benchmark.workbench.diff")}</Typography>
            </AccordionSummary>
            <AccordionDetails>
              {comparisonRows.length ? (
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>{t("benchmark.workbench.diffColField")}</TableCell>
                      <TableCell>{t("benchmark.workbench.diffColGold")}</TableCell>
                      <TableCell>{t("benchmark.workbench.diffColPred")}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {comparisonRows.map((row, idx) => {
                      const r = /** @type {Record<string, unknown>} */ (row);
                      return (
                        <TableRow key={`${r.field || r.value || "row"}-${idx}`}>
                          <TableCell>{String(r.field ?? r.value ?? "-")}</TableCell>
                          <TableCell sx={{ maxWidth: 200, wordBreak: "break-word" }}>
                            {formatComparisonCellValue(r.gold_value, r.source)}
                          </TableCell>
                          <TableCell sx={{ maxWidth: 200, wordBreak: "break-word" }}>
                            {formatComparisonCellValue(r.predicted_value, r.status ?? "-")}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              ) : (
                <Typography sx={{ color: tk.text.muted, fontSize: "0.8125rem" }}>{t("benchmark.workbench.noDiff")}</Typography>
              )}
            </AccordionDetails>
          </Accordion>
          <Accordion disableGutters elevation={0} sx={{ border: `1px solid ${tk.border.default}`, borderRadius: 1, "&:before": { display: "none" } }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography sx={{ fontSize: "0.8125rem" }}>
                {t("benchmark.inspector.raw.diagnosticsPayload")}
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <BenchmarkCaseInspectorJsonBlock value={caseDetail.diagnostics || {}} />
            </AccordionDetails>
          </Accordion>
        </Box>
      </AccordionDetails>
    </Accordion>
  );
}
