import React, { useMemo } from "react";
import Alert from "@mui/material/Alert";
import { useTheme } from "@mui/material/styles";

/**
 * Inline status / error / warning aligned with app chrome.
 *
 * @param {{
 *   severity?: "error" | "warning" | "info" | "success",
 *   children: React.ReactNode,
 *   sx?: object,
 * }} props
 */
export function InlineNotice({ severity = "warning", children, sx, ...rest }) {
  const tk = useTheme().appTokens;
  const baseSx = useMemo(
    () => ({
      fontSize: "0.8125rem",
      py: 0.5,
      backgroundColor: tk.surface.subtle,
      border: `1px solid ${tk.border.default}`,
      color: tk.text.primary,
      "& .MuiAlert-icon": {
        color: "inherit",
        opacity: 0.85,
      },
    }),
    [tk],
  );
  return (
    <Alert severity={severity} sx={{ ...baseSx, ...(sx || {}) }} {...rest}>
      {children}
    </Alert>
  );
}
