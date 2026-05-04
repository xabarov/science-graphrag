import React, { useMemo } from "react";
import BugReportOutlinedIcon from "@mui/icons-material/BugReportOutlined";
import LayersOutlinedIcon from "@mui/icons-material/LayersOutlined";
import ViewSidebarOutlinedIcon from "@mui/icons-material/ViewSidebarOutlined";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";
import { useTheme } from "@mui/material/styles";

/**
 * @param {{
 *   detailsVisible: boolean,
 *   legendOpen: boolean,
 *   diagnosticsOpen: boolean,
 *   onToggleDetails: () => void,
 *   onToggleLegend: () => void,
 *   onToggleDiagnostics: () => void,
 *   showLegendChip: boolean,
 *   showDiagnosticsChip: boolean,
 *   t: (key: string) => string,
 * }} props
 */
export default function GraphViewChips({
  detailsVisible,
  legendOpen,
  diagnosticsOpen,
  onToggleDetails,
  onToggleLegend,
  onToggleDiagnostics,
  showLegendChip,
  showDiagnosticsChip,
  t,
}) {
  const tk = useTheme().appTokens;
  const chipSx = useMemo(
    () => (active) => ({
      height: 26,
      fontSize: "0.72rem",
      fontWeight: 500,
      textTransform: "none",
      borderColor: active ? tk.accent.emphasisHoverBorder : tk.border.default,
      color: active ? tk.accent.fg : tk.text.muted,
      backgroundColor: active ? tk.accent.chipReadyBg : "transparent",
      "& .MuiChip-icon": { color: "inherit", opacity: active ? 1 : 0.72 },
      "&:hover": {
        borderColor: active ? tk.accent.emphasisHoverBorder : tk.control.outlinedBorderHover,
        backgroundColor: active ? tk.accent.emphasisHoverBg : tk.control.outlinedBgHover,
        color: active ? tk.accent.fg : tk.text.secondary,
      },
    }),
    [tk],
  );

  return (
    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, alignItems: "center" }}>
      <Tooltip title={detailsVisible ? t("graph.workspacePanel.tooltipDetailsHide") : t("graph.workspacePanel.tooltipDetailsShow")}>
        <Chip
          size="small"
          variant="outlined"
          icon={<ViewSidebarOutlinedIcon sx={{ fontSize: "1rem !important" }} />}
          label={t("graph.wsToolbar.viewChipDetails")}
          onClick={onToggleDetails}
          aria-pressed={detailsVisible}
          aria-label={t("graph.workspacePanel.ariaToggleDetails")}
          sx={chipSx(detailsVisible)}
        />
      </Tooltip>
      {showLegendChip ? (
        <Tooltip title={legendOpen ? t("graph.workspacePanel.tooltipLegendHide") : t("graph.workspacePanel.tooltipLegendShow")}>
          <Chip
            size="small"
            variant="outlined"
            icon={<LayersOutlinedIcon sx={{ fontSize: "1rem !important" }} />}
            label={t("graph.wsToolbar.viewChipLegend")}
            onClick={onToggleLegend}
            aria-pressed={legendOpen}
            aria-label={t("graph.workspacePanel.ariaToggleLegend")}
            sx={chipSx(legendOpen)}
          />
        </Tooltip>
      ) : null}
      {showDiagnosticsChip ? (
        <Tooltip
          title={diagnosticsOpen ? t("graph.workspacePanel.tooltipDiagnosticsHide") : t("graph.workspacePanel.tooltipDiagnosticsShow")}
        >
          <Chip
            size="small"
            variant="outlined"
            icon={<BugReportOutlinedIcon sx={{ fontSize: "1rem !important" }} />}
            label={t("graph.wsToolbar.viewChipDiagnostics")}
            onClick={onToggleDiagnostics}
            aria-pressed={diagnosticsOpen}
            aria-label={t("graph.workspacePanel.ariaToggleDiagnostics")}
            sx={chipSx(diagnosticsOpen)}
          />
        </Tooltip>
      ) : null}
    </Box>
  );
}
