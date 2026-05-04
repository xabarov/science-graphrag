import React from "react";
import Box from "@mui/material/Box";
import Tooltip from "@mui/material/Tooltip";
import { alpha, useTheme } from "@mui/material/styles";
import CenterFocusStrongOutlinedIcon from "@mui/icons-material/CenterFocusStrongOutlined";
import FitScreenOutlinedIcon from "@mui/icons-material/FitScreenOutlined";
import ZoomOutMapOutlinedIcon from "@mui/icons-material/ZoomOutMapOutlined";

import { CursorIconButton } from "../../common/index.js";

/**
 * Fit / reset / center — anchored bottom-right on the canvas host (does not cover bottom-left legend).
 *
 * @param {{
 *   t: (key: string) => string,
 *   onFit: () => void,
 *   onResetZoom: () => void,
 *   onCenterSelection: () => void,
 *   centerSelectionDisabled: boolean,
 * }} props
 */
export default function GraphCanvasViewportControls({ t, onFit, onResetZoom, onCenterSelection, centerSelectionDisabled }) {
  const tk = useTheme().appTokens;
  return (
    <Box
      sx={{
        position: "absolute",
        right: 10,
        bottom: 10,
        zIndex: 2,
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        gap: 0.35,
        px: 0.5,
        py: 0.35,
        borderRadius: "6px",
        border: `1px solid ${tk.border.default}`,
        backgroundColor: alpha(tk.surface.panel, 0.94),
        backdropFilter: "blur(6px)",
        pointerEvents: "auto",
      }}
    >
      <Tooltip title={t("graph.canvas.fitTooltip")}>
        <CursorIconButton type="button" aria-label={t("graph.canvas.fitAria")} onClick={onFit}>
          <FitScreenOutlinedIcon sx={{ fontSize: "1.05rem" }} />
        </CursorIconButton>
      </Tooltip>
      <Tooltip title={t("graph.canvas.resetZoomTooltip")}>
        <CursorIconButton type="button" aria-label={t("graph.canvas.resetZoomAria")} onClick={onResetZoom}>
          <ZoomOutMapOutlinedIcon sx={{ fontSize: "1.05rem" }} />
        </CursorIconButton>
      </Tooltip>
      <Tooltip title={t("graph.canvas.centerSelectionTooltip")}>
        <CursorIconButton type="button" aria-label={t("graph.canvas.centerSelectionAria")} onClick={onCenterSelection} disabled={centerSelectionDisabled}>
          <CenterFocusStrongOutlinedIcon sx={{ fontSize: "1.05rem" }} />
        </CursorIconButton>
      </Tooltip>
    </Box>
  );
}
