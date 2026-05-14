import React from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";

/**
 * Empty thread placeholder with optional starter prompt chips.
 *
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   tk: Record<string, unknown>,
 *   starterPromptKeys?: string[],
 *   onStarterPrompt?: (text: string) => void,
 * }} props
 */
export function ChatThreadEmptyState({ t, tk, starterPromptKeys = [], onStarterPrompt }) {
  return (
    <Box
      sx={{
        pb: 1.25,
        width: "100%",
        maxWidth: "min(920px, 100%)",
        mx: "auto",
      }}
    >
      <Typography sx={{ fontWeight: 600, fontSize: "0.875rem", color: tk.text.primary, mb: 0.5 }}>{t("chat.thread.emptyTitle")}</Typography>
      <Typography sx={{ fontSize: "0.8125rem", color: tk.text.muted, mb: 1.25, lineHeight: 1.45 }}>{t("chat.thread.emptySubtitle")}</Typography>
      {starterPromptKeys.length > 0 && onStarterPrompt ? (
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75 }}>
          {starterPromptKeys.map((key) => (
            <Chip
              key={key}
              size="small"
              label={t(key)}
              onClick={() => onStarterPrompt(t(key))}
              sx={{
                height: 26,
                borderRadius: "6px",
                border: `1px solid ${tk.border.strong}`,
                backgroundColor: tk.surface.subtle,
                color: tk.text.primary,
                fontSize: "0.75rem",
                maxWidth: "100%",
                "& .MuiChip-label": { px: 1, whiteSpace: "normal", textAlign: "left" },
                "&:hover": { backgroundColor: tk.accent.chipReadyBg, borderColor: tk.accent.softBorder },
              }}
            />
          ))}
        </Box>
      ) : null}
    </Box>
  );
}
