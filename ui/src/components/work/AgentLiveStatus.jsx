import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { ShimmerLabel } from "./ShimmerLabel.jsx";
import { formatStreamEventOneLine, pickLastMeaningfulStreamEvent } from "./agentRunViewModel.js";

/**
 * Compact live strip for an in-flight agent turn.
 *
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   streamEvents: unknown[],
 *   isActive: boolean,
 * }} props
 */
export function AgentLiveStatus({ t, streamEvents = [], isActive }) {
  const list = Array.isArray(streamEvents) ? streamEvents : [];
  const last = pickLastMeaningfulStreamEvent(list);
  const line = last ? formatStreamEventOneLine(t, last) : "";

  if (!isActive && !line) return null;

  return (
    <Box
      sx={{
        mb: 1.25,
        pb: 1,
        borderBottom: "1px solid rgba(255,255,255,0.06)",
      }}
    >
      <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.35)", fontSize: "0.68rem", display: "block", mb: 0.5 }}>
        {t("chat.run.liveStripTitle")}
      </Typography>
      {isActive && !line ? (
        <ShimmerLabel component="span" sx={{ fontSize: "0.78rem", fontWeight: 500 }}>
          {t("chat.stream.thinking")}
        </ShimmerLabel>
      ) : (
        <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.55)", lineHeight: 1.45, wordBreak: "break-word" }}>
          {line || t("chat.stream.thinking")}
        </Typography>
      )}
    </Box>
  );
}
