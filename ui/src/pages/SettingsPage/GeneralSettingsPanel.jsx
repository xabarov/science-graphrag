import React from "react";
import Box from "@mui/material/Box";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";

import { useI18n } from "../../i18n/I18nContext.jsx";

export default function GeneralSettingsPanel() {
  const { locale, setLocale, t } = useI18n();

  return (
    <Box
      sx={{
        border: "1px solid rgba(255,255,255,0.08)",
        backgroundColor: "#1a1a1a",
        borderRadius: 1.5,
        padding: 2.5,
      }}
    >
      <Typography sx={{ fontSize: "0.875rem", fontWeight: 600 }}>{t("settings.general.title")}</Typography>
      <Typography sx={{ marginTop: 1, fontSize: "0.8125rem", color: "rgba(255,255,255,0.58)", lineHeight: 1.6 }}>
        {t("settings.general.intro")}
      </Typography>

      <Box sx={{ marginTop: 2 }}>
        <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", marginBottom: 0.75 }}>
          {t("settings.general.languageLabel")}
        </Typography>
        <ToggleButtonGroup
          exclusive
          value={locale}
          onChange={(_e, next) => {
            if (next) setLocale(next);
          }}
          size="small"
          sx={{
            "& .MuiToggleButton-root": {
              fontSize: "0.8125rem",
              textTransform: "none",
              color: "rgba(255,255,255,0.75)",
              borderColor: "rgba(255,255,255,0.12)",
            },
            "& .Mui-selected": {
              backgroundColor: "rgba(99, 102, 241, 0.2) !important",
              color: "rgba(255,255,255,0.95)",
            },
          }}
        >
          <ToggleButton value="en" aria-label={t("settings.general.languageEnglish")}>
            {t("settings.general.languageEnglish")}
          </ToggleButton>
          <ToggleButton value="ru" aria-label={t("settings.general.languageRussian")}>
            {t("settings.general.languageRussian")}
          </ToggleButton>
        </ToggleButtonGroup>
      </Box>

      <Typography sx={{ marginTop: 1.5, fontSize: "0.72rem", color: "rgba(255,255,255,0.42)" }}>
        {t("settings.general.note")}
      </Typography>
      <Typography sx={{ marginTop: 1.5, fontSize: "0.78rem", color: "rgba(255,255,255,0.52)", lineHeight: 1.55 }}>
        {t("settings.general.envDoc")}
      </Typography>
    </Box>
  );
}
