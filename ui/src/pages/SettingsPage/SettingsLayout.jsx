import React from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { useI18n } from "../../i18n/I18nContext.jsx";
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
  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      <SettingsSectionNav sections={sections} activeSectionId={activeSectionId} onSelect={onSelectSection} />
      <Box sx={{ flex: 1, padding: 3 }}>
        <Box
          sx={{
            position: "sticky",
            top: 0,
            zIndex: 2,
            backgroundColor: "#0a0a0a",
            paddingBottom: 2,
            borderBottom: "1px solid rgba(255,255,255,0.08)",
            marginBottom: 2.5,
          }}
        >
          <Typography sx={{ fontSize: "1rem", fontWeight: 700 }}>{heading}</Typography>
          <Typography sx={{ marginTop: 0.75, fontSize: "0.8125rem", color: "rgba(255,255,255,0.58)" }}>
            {subheading}
          </Typography>
          {dirty ? (
            <Alert
              severity="info"
              sx={{
                marginTop: 1.5,
                backgroundColor: "rgba(99, 102, 241, 0.08)",
                border: "1px solid rgba(99, 102, 241, 0.18)",
                color: "rgba(255,255,255,0.85)",
                "& .MuiAlert-icon": { color: "rgba(129, 140, 248, 0.95)" },
              }}
            >
              <Typography sx={{ fontSize: "0.75rem" }}>
                {t("shell.settings.unsaved")}
              </Typography>
            </Alert>
          ) : null}
        </Box>
        {children}
      </Box>
    </Box>
  );
}
