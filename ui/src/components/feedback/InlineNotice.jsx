import React from "react";
import Alert from "@mui/material/Alert";

const baseSx = {
  fontSize: "0.8125rem",
  py: 0.5,
  backgroundColor: "rgba(255,255,255,0.04)",
  border: "1px solid rgba(255,255,255,0.08)",
  color: "rgba(255,255,255,0.88)",
  "& .MuiAlert-icon": {
    color: "inherit",
    opacity: 0.85,
  },
};

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
  return (
    <Alert severity={severity} sx={{ ...baseSx, ...(sx || {}) }} {...rest}>
      {children}
    </Alert>
  );
}
