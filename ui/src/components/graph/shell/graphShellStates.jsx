import React from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { useI18n } from "../../i18n/useI18n.js";

/**
 * Loading row used by GraphWorkspacePanel (and keeps typography aligned with the rest of the graph UI).
 */
export function GraphLoadingInline() {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1, py: 2 }}>
      <CircularProgress size={22} sx={{ color: tk.accent.fg }} />
      <Typography sx={{ fontSize: "0.8125rem", color: tk.text.muted }}>{t("graphShell.loading")}</Typography>
    </Box>
  );
}

/**
 * @param {{ children: React.ReactNode }} props
 */
export function GraphErrorAlert({ children }) {
  return (
    <Alert severity="error" sx={{ mb: 2, fontSize: "0.8125rem" }}>
      {children}
    </Alert>
  );
}

/**
 * Inline hint when no work is selected (workspace panel + graph tab).
 * @param {{ message: string }} props
 */
export function GraphMissingWorkInline({ message }) {
  const tk = useTheme().appTokens;
  return <Typography sx={{ fontSize: "0.8125rem", color: tk.text.muted }}>{message}</Typography>;
}

/**
 * Standalone Graph page empty state (no work_id).
 * @param {{ title: string, description: React.ReactNode, footnote?: React.ReactNode }} props
 */
export function GraphMissingWorkCallout({ title, description, footnote = null }) {
  const tk = useTheme().appTokens;
  return (
    <Box
      sx={{
        mb: 2,
        p: 2,
        borderRadius: "6px",
        border: `1px dashed ${tk.border.strong}`,
        backgroundColor: tk.control.outlinedBg,
      }}
    >
      <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: tk.text.primary }}>{title}</Typography>
      <Typography sx={{ mt: 0.75, fontSize: "0.8125rem", color: tk.text.secondary }}>{description}</Typography>
      {footnote ? (
        <Typography sx={{ mt: 1, fontSize: "0.75rem", color: tk.text.muted }}>{footnote}</Typography>
      ) : null}
    </Box>
  );
}
