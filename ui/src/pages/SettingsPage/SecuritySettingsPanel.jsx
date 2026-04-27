import React, { useMemo } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { useI18n } from "../../i18n/useI18n.js";
import { settingsAlertMutedSx, settingsCardSx } from "../../theme/settingsFormSx.js";

export default function SecuritySettingsPanel({ security }) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const cardSx = useMemo(() => settingsCardSx(tk), [tk]);
  const alertMutedSx = useMemo(() => settingsAlertMutedSx(tk), [tk]);

  const s = security || {};
  const adminOn = Boolean(s.admin_api_key_configured);
  const settingsAuth = Boolean(s.settings_auth_required);

  return (
    <Box
      sx={{
        ...cardSx,
        padding: 2.5,
        maxWidth: 640,
      }}
    >
      <Typography sx={{ fontSize: "0.875rem", fontWeight: 600, color: tk.text.primary }}>{t("settings.security.title")}</Typography>
      <Typography sx={{ marginTop: 1, fontSize: "0.8125rem", color: tk.text.secondary, lineHeight: 1.6 }}>
        {t("settings.security.intro")}
      </Typography>

      <Alert
        severity="info"
        sx={{
          marginTop: 2,
          ...alertMutedSx,
        }}
      >
        <Typography sx={{ fontSize: "0.8125rem", lineHeight: 1.55, color: tk.text.primary }}>
          {t("settings.security.adminKeyLine", { state: adminOn ? t("settings.security.on") : t("settings.security.off") })}
        </Typography>
        <Typography sx={{ fontSize: "0.8125rem", lineHeight: 1.55, marginTop: 1, color: tk.text.primary }}>
          {settingsAuth
            ? t("settings.security.settingsBearerOn")
            : t("settings.security.settingsBearerOff")}
        </Typography>
      </Alert>
    </Box>
  );
}
