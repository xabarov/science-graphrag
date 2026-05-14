import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { ShimmerLabel } from "../shared/ShimmerLabel.jsx";
import { decisionFadeIn } from "./agentLiveStatusKeyframes.js";

/**
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   tk: import("@mui/material/styles").Theme["appTokens"],
 *   reducedMotion: boolean,
 *   isActive: boolean,
 *   headline: string,
 * }} props
 */
export function AgentLiveStatusHeadlineRegion({ t, tk, reducedMotion, isActive, headline }) {
  return (
    <Box aria-live="polite" aria-atomic="false">
      {isActive && !headline ? (
        <ShimmerLabel component="span" intensity="subtle" sx={{ fontSize: "0.8125rem", fontWeight: 600 }}>
          {t("chat.stream.thinking")}
        </ShimmerLabel>
      ) : isActive && headline ? (
        <ShimmerLabel
          component="span"
          intensity="strong"
          sx={{
            fontSize: "0.8125rem",
            fontWeight: 600,
            lineHeight: 1.45,
            wordBreak: "break-word",
            maxWidth: "100%",
          }}
        >
          {headline}
        </ShimmerLabel>
      ) : (
        <Typography
          key={headline}
          sx={{
            fontSize: "0.8125rem",
            fontWeight: 600,
            color: tk.text.primary,
            lineHeight: 1.45,
            wordBreak: "break-word",
            transition: "opacity 0.18s ease",
            ...(reducedMotion ? {} : { animation: `${decisionFadeIn} 0.18s ease` }),
          }}
        >
          {headline || t("chat.stream.thinking")}
        </Typography>
      )}
    </Box>
  );
}
