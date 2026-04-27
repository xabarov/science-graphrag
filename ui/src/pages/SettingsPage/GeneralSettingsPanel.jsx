import React from "react";
import Box from "@mui/material/Box";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { useI18n } from "../../i18n/useI18n.js";
import { useAppearance } from "../../theme/useAppearance.js";

export default function GeneralSettingsPanel() {
  const { locale, setLocale, t } = useI18n();
  const { preference, setPreference } = useAppearance();
  const muiTheme = useTheme();
  const tk = muiTheme.appTokens;

  const toggleSx = {
    "& .MuiToggleButton-root": {
      fontSize: "0.8125rem",
      textTransform: "none",
      color: tk.text.secondary,
      borderColor: tk.border.strong,
    },
    "& .Mui-selected": {
      backgroundColor: `${tk.accent.softBg} !important`,
      color: tk.text.primary,
      borderColor: tk.accent.softBorder,
    },
  };

  return (
    <Box
      sx={{
        border: `1px solid ${tk.border.default}`,
        backgroundColor: tk.surface.panel,
        borderRadius: 1.5,
        padding: 2.5,
      }}
    >
      <Typography sx={{ fontSize: "0.875rem", fontWeight: 600, color: tk.text.primary }}>{t("settings.general.title")}</Typography>
      <Typography sx={{ marginTop: 1, fontSize: "0.8125rem", color: tk.text.secondary, lineHeight: 1.6 }}>
        {t("settings.general.intro")}
      </Typography>

      <Box sx={{ marginTop: 2 }}>
        <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted, marginBottom: 0.75 }}>{t("settings.general.languageLabel")}</Typography>
        <ToggleButtonGroup
          exclusive
          value={locale}
          onChange={(_e, next) => {
            if (next) setLocale(next);
          }}
          size="small"
          sx={toggleSx}
        >
          <ToggleButton value="en" aria-label={t("settings.general.languageEnglish")}>
            {t("settings.general.languageEnglish")}
          </ToggleButton>
          <ToggleButton value="ru" aria-label={t("settings.general.languageRussian")}>
            {t("settings.general.languageRussian")}
          </ToggleButton>
        </ToggleButtonGroup>
      </Box>

      <Box sx={{ marginTop: 2 }}>
        <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted, marginBottom: 0.75 }}>{t("settings.general.appearanceLabel")}</Typography>
        <ToggleButtonGroup
          exclusive
          value={preference}
          onChange={(_e, next) => {
            if (next) setPreference(next);
          }}
          size="small"
          sx={toggleSx}
        >
          <ToggleButton value="dark" aria-label={t("settings.general.appearanceDark")}>
            {t("settings.general.appearanceDark")}
          </ToggleButton>
          <ToggleButton value="light" aria-label={t("settings.general.appearanceLight")}>
            {t("settings.general.appearanceLight")}
          </ToggleButton>
          <ToggleButton value="system" aria-label={t("settings.general.appearanceSystem")}>
            {t("settings.general.appearanceSystem")}
          </ToggleButton>
        </ToggleButtonGroup>
      </Box>

      <Typography sx={{ marginTop: 1.5, fontSize: "0.72rem", color: tk.text.muted }}>{t("settings.general.appearanceNote")}</Typography>
      <Typography sx={{ marginTop: 1.5, fontSize: "0.72rem", color: tk.text.muted }}>{t("settings.general.note")}</Typography>
      <Typography sx={{ marginTop: 1.5, fontSize: "0.78rem", color: tk.text.secondary, lineHeight: 1.55 }}>{t("settings.general.envDoc")}</Typography>
    </Box>
  );
}
