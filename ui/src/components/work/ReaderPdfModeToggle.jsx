import React from "react";
import Box from "@mui/material/Box";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Tooltip from "@mui/material/Tooltip";
import DocumentScannerOutlinedIcon from "@mui/icons-material/DocumentScannerOutlined";
import PictureAsPdfOutlinedIcon from "@mui/icons-material/PictureAsPdfOutlined";

import { useI18n } from "../../i18n/I18nContext.jsx";

/**
 * PDF vs OCR (recognized text) view — icon toggle with tooltips.
 *
 * @param {{ viewMode: "pdf" | "ocr", onViewModeChange: (v: "pdf" | "ocr") => void }} props
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
            px: 1.15,
            py: 0.65,
            border: "1px solid rgba(255,255,255,0.12)",
            color: "rgba(255,255,255,0.55)",
            "&:hover": {
              backgroundColor: "rgba(255,255,255,0.05)",
              borderColor: "rgba(255,255,255,0.18)",
            },
          },
          "& .MuiToggleButtonGroup-grouped": {
            borderColor: "rgba(255,255,255,0.12)",
          },
          "& .Mui-selected": {
            backgroundColor: "rgba(99,102,241,0.15)",
            color: "rgba(129,140,248,0.95)",
            borderColor: "rgba(99,102,241,0.35)",
            "&:hover": {
              backgroundColor: "rgba(99,102,241,0.2)",
            },
          },
        }}
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
