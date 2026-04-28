import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { formatStreamEventOneLine } from "./agentRunViewModel.js";

/**
 * Full stream event list for inspector / debug views.
 *
 * @param {{ t: (key: string, vars?: Record<string, string>) => string, events: unknown[] }} props
 */
export function AgentStreamEventLines({ t, events }) {
  if (!Array.isArray(events) || events.length === 0) return null;
  return (
    <Box sx={{ mb: 1 }}>
      <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.4)", fontSize: "0.7rem", display: "block", mb: 0.5 }}>
        {t("chat.stream.statusTitle")}
      </Typography>
      {events.map((event, index) => {
        const type = String(event?.type || "");
        const key = `${index}-${type}`;
        const line = formatStreamEventOneLine(t, event);
        if (line) {
          const err = type === "tool_result" && event?.error;
          return (
            <Typography
              key={key}
              sx={{
                fontSize: "0.68rem",
                color: err ? "rgba(239,68,68,0.85)" : "rgba(255,255,255,0.45)",
                py: 0.15,
              }}
            >
              {line}
            </Typography>
          );
        }
        if (!type) return null;
        return (
          <Typography key={key} sx={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.35)", fontFamily: "monospace" }}>
            {type}
          </Typography>
        );
      })}
    </Box>
  );
}
