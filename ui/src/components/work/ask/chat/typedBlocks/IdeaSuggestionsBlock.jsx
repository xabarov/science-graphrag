import React, { useMemo } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { typedBlockOuterSx } from "../../../../../theme/chatTypedBlockSx.js";

/**
 * @param {{ t: (key: string, vars?: Record<string, string>) => string, suggestions: Array<Record<string, unknown>> | null | undefined }}
 */
export function IdeaSuggestionsBlock({ t, suggestions }) {
  const tk = useTheme().appTokens;
  const outer = useMemo(() => typedBlockOuterSx(tk), [tk]);

  if (!Array.isArray(suggestions) || suggestions.length === 0) return null;
  return (
    <Box sx={outer}>
      <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted, mb: 0.75 }}>{t("chat.typed.ideaSuggestionsTitle")}</Typography>
      {suggestions.slice(0, 12).map((row, i) => (
        <Typography key={i} sx={{ fontSize: "0.78rem", color: tk.text.secondary, mb: 0.5, whiteSpace: "pre-wrap" }}>
          {typeof row === "string" ? row.slice(0, 800) : JSON.stringify(row).slice(0, 800)}
        </Typography>
      ))}
    </Box>
  );
}
