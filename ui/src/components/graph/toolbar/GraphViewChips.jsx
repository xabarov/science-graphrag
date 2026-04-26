import React from "react";
import BugReportOutlinedIcon from "@mui/icons-material/BugReportOutlined";
import LayersOutlinedIcon from "@mui/icons-material/LayersOutlined";
import ViewSidebarOutlinedIcon from "@mui/icons-material/ViewSidebarOutlined";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";

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
  const chipSx = (active) => ({
    height: 26,
    fontSize: "0.72rem",
    fontWeight: 500,
    textTransform: "none",
    borderColor: active ? "rgba(99,102,241,0.45)" : "rgba(255,255,255,0.12)",
    color: active ? "rgba(129,140,248,0.95)" : "rgba(255,255,255,0.65)",
    backgroundColor: active ? "rgba(99,102,241,0.12)" : "transparent",
    "& .MuiChip-icon": { color: "inherit" },
    "&:hover": {
      borderColor: active ? "rgba(99,102,241,0.55)" : "rgba(255,255,255,0.18)",
      backgroundColor: active ? "rgba(99,102,241,0.16)" : "rgba(255,255,255,0.04)",
    },
  });

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
