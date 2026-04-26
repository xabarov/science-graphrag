import React from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";

import { useI18n } from "../../i18n/useI18n.js";

/** Shared muted body text for graph empty/loading hints (Phase 4.4). */
export const graphShellMutedTextSx = {
  fontSize: "0.8125rem",
  color: "rgba(255,255,255,0.5)",
};

/**
 * Loading row used by GraphWorkspacePanel (and keeps typography aligned with the rest of the graph UI).
 */
export function GraphLoadingInline() {
  const { t } = useI18n();
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1, py: 2 }}>
      <CircularProgress size={22} sx={{ color: "rgba(129,140,248,0.9)" }} />
      <Typography sx={graphShellMutedTextSx}>{t("graphShell.loading")}</Typography>
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
  return <Typography sx={graphShellMutedTextSx}>{message}</Typography>;
}

const calloutBoxSx = {
  mb: 2,
  p: 2,
  borderRadius: "6px",
  border: "1px dashed rgba(255,255,255,0.12)",
  backgroundColor: "rgba(255,255,255,0.02)",
};

/**
 * Standalone Graph page empty state (no work_id).
 * @param {{ title: string, description: React.ReactNode, footnote?: React.ReactNode }} props
 */
export function GraphMissingWorkCallout({ title, description, footnote = null }) {
  return (
    <Box sx={calloutBoxSx}>
      <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: "rgba(255,255,255,0.85)" }}>{title}</Typography>
      <Typography sx={{ mt: 0.75, fontSize: "0.8125rem", color: "rgba(255,255,255,0.55)" }}>{description}</Typography>
      {footnote ? (
        <Typography sx={{ mt: 1, fontSize: "0.75rem", color: "rgba(255,255,255,0.42)" }}>{footnote}</Typography>
      ) : null}
    </Box>
  );
}
