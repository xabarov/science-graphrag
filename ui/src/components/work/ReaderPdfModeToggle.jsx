import React from "react";
import Box from "@mui/material/Box";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";

import { useI18n } from "../../i18n/I18nContext.jsx";

/**
 * @param {{ viewMode: string, onViewModeChange: (v: string) => void }} props
 */
export default function ReaderPdfModeToggle({ viewMode, onViewModeChange }) {
  const { t } = useI18n();

  return (
    <Box sx={{ mb: 1.5, display: "flex", flexWrap: "wrap", alignItems: "center", gap: 1 }}>
      <ToggleButtonGroup
        size="small"
        exclusive
        value={viewMode}
        onChange={(_e, v) => {
          if (v) onViewModeChange(v);
        }}
        sx={{
          "& .MuiToggleButton-root": {
            fontSize: "0.75rem",
            py: 0.25,
            px: 1,
            textTransform: "none",
          },
        }}
      >
        <ToggleButton value="markdown">{t("readerBody.viewMarkdown")}</ToggleButton>
        <ToggleButton value="pdf">{t("readerBody.viewPdf")}</ToggleButton>
      </ToggleButtonGroup>
    </Box>
  );
}
