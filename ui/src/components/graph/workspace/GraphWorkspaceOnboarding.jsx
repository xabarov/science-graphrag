import React, { useState } from "react";
import Alert from "@mui/material/Alert";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

const SESSION_KEY = "graphWorkspaceOnboardingDismissed";

/**
 * One-time (per browser session) hints for the workspace graph chrome.
 *
 * @param {{ t: (k: string) => string }} props
 */
export default function GraphWorkspaceOnboarding({ t }) {
  const tk = useTheme().appTokens;
  const [open, setOpen] = useState(() => {
    if (typeof window === "undefined") return false;
    try {
      return window.sessionStorage.getItem(SESSION_KEY) !== "1";
    } catch {
      return true;
    }
  });

  if (!open) return null;

  const dismiss = () => {
    setOpen(false);
    try {
      window.sessionStorage.setItem(SESSION_KEY, "1");
    } catch {
      /* ignore */
    }
  };

  return (
    <Alert
      severity="info"
      variant="outlined"
      onClose={dismiss}
      sx={{ mb: 1, py: 0.5, borderColor: tk.border.default, "& .MuiAlert-message": { width: "100%" } }}
    >
      <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: tk.text.primary, mb: 0.35 }}>
        {t("graph.onboarding.title")}
      </Typography>
      <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary, lineHeight: 1.45 }}>
        {t("graph.onboarding.body")}
      </Typography>
    </Alert>
  );
}
