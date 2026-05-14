import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { decisionFadeIn, decisionGlow } from "./agentLiveStatusKeyframes.js";

/**
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   tk: import("@mui/material/styles").Theme["appTokens"],
 *   reducedMotion: boolean,
 *   decision: string,
 *   why: string,
 *   latestAgentNote: string,
 *   decisionKey: string,
 *   isSimple: boolean,
 * }} props
 */
export function AgentLiveStatusDecisionSection({
  t,
  tk,
  reducedMotion,
  decision,
  why,
  latestAgentNote,
  decisionKey,
  isSimple,
}) {
  if (!(decision || why || (!isSimple && latestAgentNote))) return null;
  return (
    <Box
      key={`${decisionKey}|${latestAgentNote}`}
      role="group"
      aria-label={t("chat.run.decision.label")}
      sx={{
        mb: 0.6,
        display: "flex",
        flexDirection: "column",
        gap: 0.15,
        borderRadius: "4px",
        ...(reducedMotion
          ? {}
          : {
              animation: `${decisionFadeIn} 0.22s ease, ${decisionGlow} 0.6s ease`,
            }),
      }}
    >
      {decision ? (
        <Typography
          sx={{
            fontSize: "0.72rem",
            color: tk.text.secondary,
            lineHeight: 1.4,
            wordBreak: "break-word",
          }}
        >
          {t("chat.run.decision.row", { label: t("chat.run.decision.label"), value: decision })}
        </Typography>
      ) : null}
      {why ? (
        <Typography
          sx={{
            fontSize: "0.72rem",
            color: tk.text.muted,
            lineHeight: 1.4,
            wordBreak: "break-word",
          }}
        >
          {t("chat.run.decision.row", { label: t("chat.run.decision.why"), value: why })}
        </Typography>
      ) : null}
      {!isSimple && latestAgentNote ? (
        <Typography
          data-testid="agent-note-row"
          sx={{
            fontSize: "0.72rem",
            color: tk.text.muted,
            fontStyle: "italic",
            lineHeight: 1.4,
            wordBreak: "break-word",
          }}
        >
          {t("chat.run.decision.row", {
            label: t("chat.run.agentNote.label"),
            value: latestAgentNote,
          })}
        </Typography>
      ) : null}
    </Box>
  );
}
