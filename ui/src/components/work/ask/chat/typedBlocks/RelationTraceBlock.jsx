import React, { useMemo } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { typedBlockOuterSx } from "../../../../../theme/chatTypedBlockSx.js";

/**
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   relationTrace: Record<string, unknown> | null | undefined,
 *   chatDetailLevel?: "simple" | "detailed",
 * }}
 */
export function RelationTraceBlock({ t, relationTrace, chatDetailLevel = "simple" }) {
  const tk = useTheme().appTokens;
  const outer = useMemo(() => typedBlockOuterSx(tk), [tk]);

  if (chatDetailLevel !== "detailed") return null;
  if (!relationTrace || typeof relationTrace !== "object") return null;
  const keys = Object.keys(relationTrace);
  if (keys.length === 0) return null;
  const raw = JSON.stringify(relationTrace, null, 2);
  return (
    <Box sx={outer}>
      <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted, mb: 0.75 }}>{t("chat.typed.relationTraceTitle")}</Typography>
      <Typography
        component="pre"
        sx={{ fontSize: "0.7rem", m: 0, whiteSpace: "pre-wrap", wordBreak: "break-word", color: tk.text.secondary }}
      >
        {raw.slice(0, 6000)}
        {raw.length > 6000 ? "…" : ""}
      </Typography>
    </Box>
  );
}
