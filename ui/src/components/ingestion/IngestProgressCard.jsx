import React from "react";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Box from "@mui/material/Box";
import LinearProgress from "@mui/material/LinearProgress";
import Typography from "@mui/material/Typography";

import IngestStageRow from "./IngestStageRow.jsx";
import { useI18n } from "../../i18n/I18nContext.jsx";

/**
 * @param {{ ingestJob: object }} props
 */
export default function IngestProgressCard({ ingestJob }) {
  const { t } = useI18n();
  const pctRaw =
    typeof ingestJob?.progress_pct === "number" && Number.isFinite(ingestJob.progress_pct)
      ? Math.min(100, Math.max(0, ingestJob.progress_pct * 100))
      : Math.min(100, Math.max(0, Number(ingestJob?.progress_current) || 0));

  return (
    <Box sx={{ mt: 1.5 }}>
      <Typography sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.5)", fontFamily: "monospace" }}>
        {t("workspace.upload.jobLine", { id: String(ingestJob.job_id), status: String(ingestJob.status) })}
      </Typography>
      <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.65)", mt: 0.5 }}>
        {ingestJob.message || t("workspace.upload.dash")}
      </Typography>
      <Typography sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.42)", mt: 0.75 }}>
        {t("workspace.ingest.progressLabel", { pct: String(Math.round(pctRaw)) })}
      </Typography>
      <LinearProgress
        variant="determinate"
        value={pctRaw}
        sx={{
          mt: 0.5,
          height: 6,
          borderRadius: 2,
          backgroundColor: "rgba(255,255,255,0.06)",
          "& .MuiLinearProgress-bar": { backgroundColor: "rgba(129,140,248,0.85)" },
        }}
      />
      {Array.isArray(ingestJob.stages) && ingestJob.stages.length ? (
        <Box sx={{ mt: 1.25 }}>
          {ingestJob.stages.map((st, idx) => {
            const active =
              String(st?.status || "").toLowerCase() === "running" ||
              (idx === ingestJob.stages.length - 1 &&
                !ingestJob.stages.some((s) => String(s?.status || "").toLowerCase() === "running"));
            return <IngestStageRow key={`${st?.stage || idx}`} stage={st} active={Boolean(active)} />;
          })}
        </Box>
      ) : null}
      {ingestJob.work_id ? (
        <Typography sx={{ fontSize: "0.72rem", color: "rgba(129,140,248,0.9)", mt: 0.75 }}>
          {t("workspace.upload.newWorkId")} <code>{ingestJob.work_id}</code>
        </Typography>
      ) : null}
      {ingestJob.logs ? (
        <Accordion
          defaultExpanded={false}
          disableGutters
          sx={{
            mt: 1.25,
            backgroundColor: "#141414",
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: "6px",
            "&:before": { display: "none" },
          }}
        >
          <AccordionSummary sx={{ fontSize: "0.72rem", minHeight: 32 }}>
            {t("workspace.ingest.detailsLogs")}
          </AccordionSummary>
          <AccordionDetails sx={{ pt: 0 }}>
            <Box
              component="pre"
              sx={{
                maxHeight: 140,
                overflow: "auto",
                fontSize: "0.65rem",
                color: "rgba(255,255,255,0.45)",
                backgroundColor: "#0a0a0a",
                p: 1,
                borderRadius: "4px",
                border: "1px solid rgba(255,255,255,0.08)",
              }}
            >
              {ingestJob.logs}
            </Box>
          </AccordionDetails>
        </Accordion>
      ) : null}
    </Box>
  );
}
