import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { useI18n } from "../../i18n/I18nContext.jsx";

function Row({ label, value }) {
  return (
    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, py: 0.75, borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
      <Typography sx={{ minWidth: 140, fontSize: "0.75rem", color: "rgba(255,255,255,0.5)" }}>{label}</Typography>
      <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.88)", fontFamily: "ui-monospace, monospace" }}>
        {value ?? "—"}
      </Typography>
    </Box>
  );
}

export default function DiagnosticsSettingsPanel({ diagnostics }) {
  const { t } = useI18n();
  const d = diagnostics || {};

  return (
    <Box
      sx={{
        border: "1px solid rgba(255,255,255,0.08)",
        backgroundColor: "#1a1a1a",
        borderRadius: 1.5,
        padding: 2.5,
        maxWidth: 640,
      }}
    >
      <Typography sx={{ fontSize: "0.875rem", fontWeight: 600 }}>{t("settings.diagnostics.title")}</Typography>
      <Typography sx={{ marginTop: 1, fontSize: "0.8125rem", color: "rgba(255,255,255,0.58)", lineHeight: 1.6 }}>
        {t("settings.diagnostics.intro")}
      </Typography>
      <Box sx={{ marginTop: 2 }}>
        <Row label={t("settings.diagnostics.appVersion")} value={d.app_version} />
        <Row label={t("settings.diagnostics.pythonVersion")} value={d.python_version} />
        <Row label={t("settings.diagnostics.inDocker")} value={d.in_docker ? t("settings.diagnostics.yes") : t("settings.diagnostics.no")} />
        <Row label={t("settings.diagnostics.gitCommit")} value={d.git_commit || t("settings.diagnostics.notSet")} />
      </Box>
    </Box>
  );
}
