import React from "react";
import Alert from "@mui/material/Alert";
import Typography from "@mui/material/Typography";

/**
 * Page chrome (title/body) or compact chat eyebrow + submit/stream errors.
 *
 * @param {{
 *   showPageChrome: boolean,
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   scopeEyebrow: string,
 *   error: string | null,
 * }} props
 */
export function AskPanelChrome({ showPageChrome, t, scopeEyebrow, error }) {
  return (
    <>
      {showPageChrome ? (
        <>
          <Typography sx={{ fontWeight: 600, mb: 0.5, color: "rgba(255,255,255,0.9)" }}>{t("askPanel.chromeTitle")}</Typography>
          <Typography sx={{ color: "rgba(255,255,255,0.55)", fontSize: "0.8125rem", mb: 1 }}>{t("askPanel.chromeBody")}</Typography>
        </>
      ) : (
        <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", mb: 0.5, flexShrink: 0 }} noWrap title={scopeEyebrow}>
          {scopeEyebrow}
        </Typography>
      )}
      {error ? (
        <Alert severity="error" sx={{ fontSize: "0.8125rem", flexShrink: 0, py: 0.5 }}>
          {error}
        </Alert>
      ) : null}
    </>
  );
}
