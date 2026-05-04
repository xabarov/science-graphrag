import React from "react";
import Box from "@mui/material/Box";
import LinearProgress from "@mui/material/LinearProgress";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";

import { INGEST_PHASE_KEYS } from "../../components/ingestion/ingestStripModel.js";
import { ShimmerLabel } from "../../components/work/shared/ShimmerLabel.jsx";

/**
 * @param {Record<string, unknown> | null | undefined} job
 * @returns {number | null}
 */
function pickIngestJobRemainingEtaMs(job) {
  if (!job || typeof job !== "object") return null;
  const keys = [
    "remaining_duration_ms",
    "remainingDurationMs",
    "aggregate_remaining_duration_ms",
    "eta_remaining_ms",
    "expected_remaining_duration_ms",
  ];
  for (const k of keys) {
    const v = job[k];
    if (typeof v === "number" && Number.isFinite(v) && v > 0) return v;
  }
  return null;
}

/**
 * Ingest upload/progress column in the workspace context strip.
 */
export default function WorkspaceIngestProgressStrip({
  tk,
  t,
  hasWs,
  ingestBusy,
  progressValue,
  ingestIndeterminate,
  ingestStrip,
  ingestStageSecondary,
  ingestPhaseIdx,
}) {
  if (!hasWs || !ingestBusy) return null;

  const job = ingestStrip?.job && typeof ingestStrip.job === "object" ? ingestStrip.job : null;
  const remainingEtaMs = pickIngestJobRemainingEtaMs(job);
  const etaLine =
    remainingEtaMs != null
      ? t("workspace.strip.ingestRemainingEta", { sec: String(Math.max(1, Math.round(remainingEtaMs / 1000))) })
      : null;

  return (
    <Box sx={{ width: { xs: "100%", md: 260 }, flexShrink: 0, minWidth: 0 }}>
      <Tooltip
        title={
          <Stack spacing={0.75} sx={{ maxWidth: 280 }}>
            <Typography sx={{ fontSize: "0.75rem", fontWeight: 600, color: "common.white" }}>
              {t("workspace.strip.ingestProgressTip")}
            </Typography>
            <Typography sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.82)", lineHeight: 1.45 }}>
              {t("workspace.strip.ingestProgressTwoScalesHint")}
            </Typography>
          </Stack>
        }
      >
        <Stack spacing={0.35}>
          <Stack direction="row" alignItems="center" justifyContent="space-between" gap={0.5}>
            <Box sx={{ minWidth: 0, flex: 1 }}>
              {ingestStrip?.failed ? (
                <Typography sx={{ fontSize: "0.72rem", color: tk.state.dangerFg, fontWeight: 500 }} noWrap>
                  {t("workspace.strip.ingestFailed")}
                </Typography>
              ) : ingestStrip?.starting ? (
                <ShimmerLabel component="span" sx={{ fontSize: "0.72rem", fontWeight: 500 }}>
                  {t("workspace.strip.ingestStarting")}
                </ShimmerLabel>
              ) : (
                <ShimmerLabel component="span" sx={{ fontSize: "0.72rem", fontWeight: 500 }}>
                  {t(`workspace.strip.ingestPhase.${ingestStrip?.phaseKey || "preparing_document"}`)}
                </ShimmerLabel>
              )}
            </Box>
            {!ingestIndeterminate && progressValue != null ? (
              <Typography sx={{ fontSize: "0.68rem", color: tk.text.faint, flexShrink: 0 }}>
                {`${Math.round(progressValue)}%`}
              </Typography>
            ) : null}
          </Stack>
          {ingestStrip && !ingestStrip.starting && !ingestStrip.failed
            ? (() => {
                const j = ingestStrip.job;
                const dm = j?.detail_message && String(j.detail_message).trim();
                const sc = typeof j?.subprogress_current === "number" ? j.subprogress_current : null;
                const st = typeof j?.subprogress_total === "number" ? j.subprogress_total : null;
                const subStr = sc != null && st != null && st > 0 ? `${Math.round(sc)}/${Math.round(st)}` : null;
                const core = dm || ingestStageSecondary || (j?.message ? String(j.message).slice(0, 72) : "");
                const line = [subStr, core].filter(Boolean).join(" · ");
                if (!line) return null;
                return (
                  <Typography sx={{ fontSize: "0.65rem", color: tk.text.faint }} noWrap title={ingestStrip.stageId}>
                    {line.length > 96 ? `${line.slice(0, 96)}…` : line}
                  </Typography>
                );
              })()
            : null}
          <LinearProgress
            variant={ingestIndeterminate ? "indeterminate" : progressValue != null ? "determinate" : "indeterminate"}
            value={!ingestIndeterminate && progressValue != null ? progressValue : undefined}
            sx={{
              height: 4,
              borderRadius: 2,
              backgroundColor: tk.control.chipMutedBg,
              "& .MuiLinearProgress-bar": {
                backgroundColor: ingestStrip?.failed ? tk.state.dangerFg : tk.accent.fg,
              },
            }}
          />
          {etaLine ? (
            <Typography sx={{ fontSize: "0.62rem", color: tk.text.faint, mt: 0.25 }}>{etaLine}</Typography>
          ) : null}
          {!ingestStrip?.failed && !ingestStrip?.starting ? (
            <Stack direction="row" spacing={0.35} sx={{ mt: 0.4 }} aria-hidden>
              {INGEST_PHASE_KEYS.map((pk, i) => {
                const done = i < ingestPhaseIdx;
                const active = i === ingestPhaseIdx;
                return (
                  <Box
                    key={pk}
                    sx={{
                      flex: 1,
                      height: 3,
                      borderRadius: 1,
                      backgroundColor: done || active ? tk.accent.softBorder : tk.control.chipMutedBg,
                      opacity: active ? 1 : done ? 0.85 : 1,
                    }}
                  />
                );
              })}
            </Stack>
          ) : null}
        </Stack>
      </Tooltip>
    </Box>
  );
}
