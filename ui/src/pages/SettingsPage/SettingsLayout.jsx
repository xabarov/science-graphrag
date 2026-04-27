import React from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { useI18n } from "../../i18n/useI18n.js";
import SettingsSectionNav from "./SettingsSectionNav.jsx";

export default function SettingsLayout({
  sections,
  activeSectionId,
  onSelectSection,
  heading,
  subheading,
  dirty,
  children,
}) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      <SettingsSectionNav sections={sections} activeSectionId={activeSectionId} onSelect={onSelectSection} />
      <Box sx={{ flex: 1, padding: 3 }}>
        <Box
          sx={{
            position: "sticky",
            top: 0,
            zIndex: 2,
            backgroundColor: tk.surface.app,
            paddingBottom: 2,
            borderBottom: `1px solid ${tk.border.default}`,
            marginBottom: 2.5,
          }}
        >
          <Typography sx={{ fontSize: "1rem", fontWeight: 700, color: tk.text.primary }}>{heading}</Typography>
          <Typography sx={{ marginTop: 0.75, fontSize: "0.8125rem", color: tk.text.secondary }}>{subheading}</Typography>
          {dirty ? (
            <Alert
              severity="info"
              sx={{
                marginTop: 1.5,
                backgroundColor: tk.accent.softBg,
                border: `1px solid ${tk.accent.softBorder}`,
                color: tk.text.primary,
                "& .MuiAlert-icon": { color: tk.accent.fg },
              }}
            >
              <Typography sx={{ fontSize: "0.75rem" }}>{t("shell.settings.unsaved")}</Typography>
            </Alert>
          ) : null}
        </Box>
        {children}
      </Box>
    </Box>
  );
}
