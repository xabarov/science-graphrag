import React, { useMemo } from "react";
import Box from "@mui/material/Box";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Tooltip from "@mui/material/Tooltip";
import { useTheme } from "@mui/material/styles";
import DocumentScannerOutlinedIcon from "@mui/icons-material/DocumentScannerOutlined";
import PictureAsPdfOutlinedIcon from "@mui/icons-material/PictureAsPdfOutlined";

import { useI18n } from "../../i18n/useI18n.js";

/**
 * PDF vs OCR (recognized text) view — icon toggle with tooltips.
 *
 * @param {{ viewMode: "pdf" | "ocr", onViewModeChange: (v: "pdf" | "ocr") => void }} props
 */
export default function ReaderPdfModeToggle({ viewMode, onViewModeChange }) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const groupSx = useMemo(
    () => ({
      "& .MuiToggleButton-root": {
        px: 1.15,
        py: 0.65,
        border: `1px solid ${tk.border.strong}`,
        color: tk.text.secondary,
        "&:hover": {
          backgroundColor: tk.control.outlinedBgHover,
          borderColor: tk.control.outlinedBorderHover,
        },
      },
      "& .MuiToggleButtonGroup-grouped": {
        borderColor: tk.border.strong,
      },
      "& .Mui-selected": {
        backgroundColor: `${tk.accent.softBg} !important`,
        color: tk.accent.fg,
        borderColor: tk.accent.softBorder,
        "&:hover": {
          backgroundColor: `${tk.accent.emphasisHoverBg} !important`,
        },
      },
    }),
    [tk],
  );

  return (
    <Box sx={{ mb: 1.5, display: "flex", flexWrap: "wrap", alignItems: "center", gap: 1 }}>
      <ToggleButtonGroup
        size="small"
        exclusive
        value={viewMode}
        onChange={(_e, v) => {
          if (v) onViewModeChange(v);
        }}
        sx={groupSx}
      >
        <Tooltip title={t("readerBody.viewOcrTooltip")} enterDelay={400}>
          <ToggleButton value="ocr" aria-label={t("readerBody.viewOcrTooltip")}>
            <DocumentScannerOutlinedIcon sx={{ fontSize: "1.2rem" }} />
          </ToggleButton>
        </Tooltip>
        <Tooltip title={t("readerBody.viewPdfTooltip")} enterDelay={400}>
          <ToggleButton value="pdf" aria-label={t("readerBody.viewPdfTooltip")}>
            <PictureAsPdfOutlinedIcon sx={{ fontSize: "1.2rem" }} />
          </ToggleButton>
        </Tooltip>
      </ToggleButtonGroup>
    </Box>
  );
}
