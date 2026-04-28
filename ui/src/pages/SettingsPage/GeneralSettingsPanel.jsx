import React, { useEffect, useMemo, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import TextField from "@mui/material/TextField";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CursorPrimaryButton } from "../../components/common/index.js";
import { useI18n } from "../../i18n/useI18n.js";
import { useAppearance } from "../../theme/useAppearance.js";
import { outlinedAppTextFieldSx, settingsCardSx } from "../../theme/settingsFormSx.js";

export default function GeneralSettingsPanel({ general, saving, saveError, onSave, onDirtyChange }) {
  const { locale, setLocale, t } = useI18n();
  const { preference, setPreference } = useAppearance();
  const muiTheme = useTheme();
  const tk = muiTheme.appTokens;
  const fieldSx = useMemo(() => outlinedAppTextFieldSx(tk), [tk]);
  const cardSx = useMemo(() => settingsCardSx(tk), [tk]);

  const resolvedMailto = (general?.effective?.resolved_openalex_mailto ?? "").trim();
  const usesEnvDefault = Boolean(general?.status?.uses_env_default);

  const [mailto, setMailto] = useState(resolvedMailto);

  useEffect(() => {
    setMailto(resolvedMailto);
  }, [resolvedMailto]);

  const mailtoDirty = mailto.trim() !== resolvedMailto;
  useEffect(() => {
    onDirtyChange?.(mailtoDirty);
  }, [mailtoDirty, onDirtyChange]);

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

  async function handleOpenAlexSubmit(event) {
    event.preventDefault();
    if (!mailtoDirty) return;
    await onSave({ openalex_mailto: mailto.trim() });
  }

  const mailtoLooksValid = mailto.includes("@") && !mailto.includes(" ");

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5 }}>
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

      <Box component="form" onSubmit={handleOpenAlexSubmit} sx={{ ...cardSx, padding: 2.5, maxWidth: 560 }}>
        <Typography sx={{ fontSize: "0.875rem", fontWeight: 600, color: tk.text.primary }}>{t("settings.general.openalex.title")}</Typography>
        <Typography sx={{ marginTop: 1, fontSize: "0.8125rem", color: tk.text.secondary, lineHeight: 1.6 }}>
          {t("settings.general.openalex.intro")}
        </Typography>

        {usesEnvDefault ? (
          <Alert
            severity="info"
            sx={{
              marginTop: 2,
              backgroundColor: tk.surface.subtle,
              border: `1px solid ${tk.border.default}`,
            }}
          >
            <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary }}>{t("settings.general.openalex.fromEnv")}</Typography>
          </Alert>
        ) : (
          <Alert
            severity="success"
            sx={{
              marginTop: 2,
              backgroundColor: tk.surface.subtle,
              border: `1px solid ${tk.border.default}`,
            }}
          >
            <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary }}>{t("settings.general.openalex.fromServer")}</Typography>
          </Alert>
        )}

        {saveError ? (
          <Alert
            severity="error"
            sx={{
              marginTop: 2,
              backgroundColor: tk.surface.subtle,
              border: `1px solid ${tk.border.default}`,
            }}
          >
            <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary }}>{saveError}</Typography>
          </Alert>
        ) : null}

        <TextField
          label={t("settings.general.openalex.fieldLabel")}
          type="email"
          value={mailto}
          onChange={(e) => setMailto(e.target.value)}
          fullWidth
          required
          sx={{ ...fieldSx, marginTop: 2.5 }}
          helperText={t("settings.general.openalex.helper")}
        />

        <Box sx={{ marginTop: 2, display: "flex", gap: 1, flexWrap: "wrap" }}>
          <CursorPrimaryButton type="submit" disabled={saving || !mailtoDirty || !mailtoLooksValid}>
            {t("settings.general.openalex.save")}
          </CursorPrimaryButton>
        </Box>
      </Box>
    </Box>
  );
}
