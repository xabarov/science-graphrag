import React from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import { chipPop } from "./agentLiveStatusKeyframes.js";

/**
 * @param {{
 *   activityChips: Array<{ tool: string, label: string }>,
 *   tk: import("@mui/material/styles").Theme["appTokens"],
 *   reducedMotion: boolean,
 * }} props
 */
export function AgentLiveStatusActivityChips({ activityChips, tk, reducedMotion }) {
  if (activityChips.length === 0) return null;
  return (
    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mt: 0.75, alignItems: "center" }}>
      {activityChips.map(({ tool, label }, chipIdx) => (
        <Chip
          key={`${tool}-${chipIdx}`}
          size="small"
          label={label}
          sx={{
            height: 22,
            fontSize: "0.68rem",
            color: tk.text.secondary,
            backgroundColor: "rgba(255,255,255,0.05)",
            border: "1px solid rgba(255,255,255,0.1)",
            maxWidth: "100%",
            transition: "border-color 0.15s ease, background-color 0.15s ease",
            ...(reducedMotion ? {} : { animation: `${chipPop} 0.18s ease` }),
          }}
        />
      ))}
    </Box>
  );
}
