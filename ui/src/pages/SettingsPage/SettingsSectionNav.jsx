import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { useI18n } from "../../i18n/useI18n.js";
import {
  resolveSettingsSectionDescription,
  resolveSettingsSectionLabel,
} from "./settingsSectionText.js";

function handleSectionKeyDown(event, sectionId, onSelect) {
  if (event.key !== "Enter" && event.key !== " ") return;
  event.preventDefault();
  onSelect(sectionId);
}

export default function SettingsSectionNav({ sections, activeSectionId, onSelect }) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  return (
    <Box
      sx={{
        width: 250,
        borderRight: `1px solid ${tk.border.default}`,
        padding: 2,
        display: "flex",
        flexDirection: "column",
        gap: 1,
      }}
    >
      <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted, letterSpacing: "0.04em" }}>
        {t("shell.settings.navTitle")}
      </Typography>
      {sections.map((section) => {
        const active = section.id === activeSectionId;
        const label = resolveSettingsSectionLabel(section, t);
        const description = resolveSettingsSectionDescription(section, t);
        return (
          <Box
            key={section.id}
            role="button"
            tabIndex={0}
            aria-current={active ? "page" : undefined}
            onClick={() => onSelect(section.id)}
            onKeyDown={(event) => handleSectionKeyDown(event, section.id, onSelect)}
            sx={{
              cursor: "pointer",
              borderRadius: 1.5,
              border: `1px solid ${active ? tk.accent.softBorder : tk.border.default}`,
              backgroundColor: active ? tk.accent.chipReadyBg : tk.surface.sidebar,
              padding: 1.25,
              transition: "all 0.15s ease",
              "&:hover": {
                borderColor: tk.border.strong,
                backgroundColor: active ? tk.accent.emphasisHoverBg : tk.control.navItemHoverBg,
              },
            }}
          >
            <Typography sx={{ fontSize: "0.8125rem", fontWeight: 600, color: tk.text.primary }}>{label}</Typography>
            <Typography sx={{ marginTop: 0.75, fontSize: "0.75rem", color: tk.text.secondary, lineHeight: 1.45 }}>
              {description}
            </Typography>
          </Box>
        );
      })}
    </Box>
  );
}
