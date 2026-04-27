import React from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { useI18n } from "../../i18n/useI18n.js";

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
        const ready = section.status === "ready";
        const labelKey = `settings.snapshot.${section.id}.label`;
        const descKey = `settings.snapshot.${section.id}.description`;
        const label = t(labelKey) !== labelKey ? t(labelKey) : section.label;
        const description = t(descKey) !== descKey ? t(descKey) : section.description;
        return (
          <Box
            key={section.id}
            onClick={() => onSelect(section.id)}
            sx={{
              cursor: "pointer",
              borderRadius: 1.5,
              border: `1px solid ${tk.border.default}`,
              backgroundColor: active ? tk.accent.chipReadyBg : tk.surface.sidebar,
              padding: 1.25,
              transition: "all 0.15s ease",
              "&:hover": {
                borderColor: tk.border.strong,
                backgroundColor: active ? tk.accent.emphasisHoverBg : tk.control.outlinedBgHover,
              },
            }}
          >
            <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1 }}>
              <Typography sx={{ fontSize: "0.8125rem", fontWeight: 600, color: tk.text.primary }}>{label}</Typography>
              <Chip
                label={ready ? t("shell.settings.statusReady") : t("shell.settings.statusSoon")}
                size="small"
                sx={{
                  height: 20,
                  fontSize: "0.6875rem",
                  backgroundColor: ready ? tk.accent.chipReadyBg : tk.control.chipMutedBg,
                  color: ready ? tk.accent.chipReadyFg : tk.control.chipMutedFg,
                  border: `1px solid ${tk.border.default}`,
                }}
              />
            </Box>
            <Typography sx={{ marginTop: 0.75, fontSize: "0.75rem", color: tk.text.secondary, lineHeight: 1.45 }}>
              {description}
            </Typography>
          </Box>
        );
      })}
    </Box>
  );
}
