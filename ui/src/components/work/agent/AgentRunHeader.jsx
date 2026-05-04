import React, { useEffect, useState } from "react";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Collapse from "@mui/material/Collapse";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

/**
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   runState: 'running' | 'done' | 'warning' | 'degraded' | 'failed',
 *   answerClass?: string | null,
 *   citationCount?: number,
 *   durationMs?: number | null,
 *   totalTokens?: number | null,
 *   progressHint?: string,
 *   defaultDetailsOpen?: boolean,
 * }} props
 */
export function AgentRunHeader({
  t,
  runState,
  answerClass = null,
  citationCount = 0,
  durationMs = null,
  totalTokens = null,
  progressHint = "",
  defaultDetailsOpen = false,
}) {
  const tk = useTheme().appTokens;
  const [detailsOpen, setDetailsOpen] = useState(defaultDetailsOpen);

  useEffect(() => {
    setDetailsOpen(defaultDetailsOpen);
  }, [defaultDetailsOpen]);

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

  const dur =
    durationMs != null && Number.isFinite(Number(durationMs)) && Number(durationMs) > 0
      ? t("chat.run.durationMs", { ms: String(Math.round(Number(durationMs))) })
      : null;

  const tok =
    totalTokens != null && Number.isFinite(Number(totalTokens)) && Number(totalTokens) >= 0
      ? t("chat.run.tokensTotal", { n: String(Math.round(Number(totalTokens))) })
      : null;

  const showDetailsToggle = runState !== "running";
  const cls = answerClass != null ? String(answerClass).trim() : "";

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
        <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 0.5, justifyContent: "flex-end" }}>
          {runState === "running" && progressHint ? (
            <Typography sx={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.38)", maxWidth: 420 }} noWrap title={progressHint}>
              {progressHint}
            </Typography>
          ) : null}
          {dur ? (
            <Typography sx={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.38)" }}>{dur}</Typography>
          ) : null}
          {showDetailsToggle ? (
            <IconButton
              type="button"
              size="small"
              aria-expanded={detailsOpen}
              aria-label={detailsOpen ? t("chat.run.headerDetailsCollapseAria") : t("chat.run.headerDetailsExpandAria")}
              title={t("chat.run.headerDetailsToggle")}
              onClick={() => setDetailsOpen((v) => !v)}
              sx={{
                color: tk.text.muted,
                p: 0.35,
                "&:hover": { backgroundColor: tk.control.navItemHoverBg },
              }}
            >
              <ExpandMoreIcon
                sx={{
                  fontSize: "1.15rem",
                  transform: detailsOpen ? "rotate(180deg)" : "none",
                  transition: "transform 0.15s ease",
                }}
              />
            </IconButton>
          ) : null}
        </Box>
      </Box>

      <Collapse in={detailsOpen && showDetailsToggle} timeout="auto" unmountOnExit>
        <Box
          sx={{
            mt: 0.75,
            pt: 0.75,
            borderTop: `1px solid ${tk.border.default}`,
            display: "flex",
            flexWrap: "wrap",
            gap: 1,
            alignItems: "center",
          }}
        >
          {cls ? (
            <Chip
              size="small"
              label={t("chat.run.answerClassChip", { cls })}
              sx={{
                height: 22,
                fontSize: "0.68rem",
                color: "rgba(255,255,255,0.55)",
                backgroundColor: "rgba(255,255,255,0.05)",
                border: "1px solid rgba(255,255,255,0.08)",
                maxWidth: "100%",
              }}
            />
          ) : null}
          {tok ? (
            <Typography sx={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.38)" }}>{tok}</Typography>
          ) : null}
          <Typography sx={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.38)" }}>
            {t("chat.run.citationsCount", { n: String(citationCount) })}
          </Typography>
        </Box>
      </Collapse>
    </Box>
  );
}
