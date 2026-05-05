import React from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";

/**
 * Compact run chrome: assistant label + run state. Answer class and models live in the metadata dialog.
 *
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   runState: 'running' | 'done' | 'warning' | 'degraded' | 'failed',
 *   progressHint?: string,
 * }} props
 */
export function AgentRunHeader({ t, runState, progressHint = "" }) {
  const stateKey =
    runState === "running"
      ? "chat.run.state.running"
      : runState === "warning"
        ? "chat.run.state.warning"
        : runState === "degraded"
          ? "chat.run.state.degraded"
          : runState === "failed"
            ? "chat.run.state.failed"
            : "chat.run.state.done";
  const stateColor =
    runState === "running"
      ? "rgba(129, 140, 248, 0.95)"
      : runState === "warning"
        ? "rgba(251, 191, 36, 0.95)"
        : runState === "degraded"
          ? "rgba(147, 197, 253, 0.92)"
          : runState === "failed"
            ? "rgba(239, 68, 68, 0.9)"
            : "rgba(255, 255, 255, 0.55)";
  const stateBg =
    runState === "running"
      ? "rgba(99, 102, 241, 0.12)"
      : runState === "warning"
        ? "rgba(251, 191, 36, 0.08)"
        : runState === "degraded"
          ? "rgba(147, 197, 253, 0.08)"
          : runState === "failed"
            ? "rgba(239, 68, 68, 0.08)"
            : "rgba(255, 255, 255, 0.06)";

  return (
    <Box sx={{ mb: 1.25 }}>
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 1,
          rowGap: 0.75,
        }}
      >
        <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 0.75, minWidth: 0 }}>
          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: "rgba(255,255,255,0.88)" }}>
            {t("chat.run.assistantLabel")}
          </Typography>
          <Chip
            size="small"
            label={t(stateKey)}
            sx={{
              height: 22,
              fontSize: "0.7rem",
              color: stateColor,
              backgroundColor: stateBg,
              border: "1px solid rgba(255,255,255,0.1)",
            }}
          />
        </Box>
        <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 0.5, justifyContent: "flex-end", minHeight: 28 }}>
          {runState === "running" && progressHint ? (
            <Typography sx={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.38)", maxWidth: 420 }} noWrap title={progressHint}>
              {progressHint}
            </Typography>
          ) : null}
        </Box>
      </Box>
    </Box>
  );
}
