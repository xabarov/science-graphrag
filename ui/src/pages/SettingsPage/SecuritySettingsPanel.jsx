import React from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { useI18n } from "../../i18n/I18nContext.jsx";

export default function SecuritySettingsPanel({ security }) {
  const { t } = useI18n();
  const s = security || {};
  const adminOn = Boolean(s.admin_api_key_configured);
  const settingsAuth = Boolean(s.settings_auth_required);

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
      <Typography sx={{ fontSize: "0.875rem", fontWeight: 600 }}>{t("settings.security.title")}</Typography>
      <Typography sx={{ marginTop: 1, fontSize: "0.8125rem", color: "rgba(255,255,255,0.58)", lineHeight: 1.6 }}>
        {t("settings.security.intro")}
      </Typography>

      <Alert
        severity="info"
        sx={{
          marginTop: 2,
          backgroundColor: "rgba(255,255,255,0.03)",
          border: "1px solid rgba(255,255,255,0.08)",
          color: "rgba(255,255,255,0.85)",
          "& .MuiAlert-icon": { color: "inherit" },
        }}
      >
        <Typography sx={{ fontSize: "0.8125rem", lineHeight: 1.55 }}>
          {t("settings.security.adminKeyLine", { state: adminOn ? t("settings.security.on") : t("settings.security.off") })}
        </Typography>
        <Typography sx={{ fontSize: "0.8125rem", lineHeight: 1.55, marginTop: 1 }}>
          {settingsAuth
            ? t("settings.security.settingsBearerOn")
            : t("settings.security.settingsBearerOff")}
        </Typography>
      </Alert>
    </Box>
  );
}
