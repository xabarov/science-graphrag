import React from "react";
import Box from "@mui/material/Box";
import Divider from "@mui/material/Divider";
import FormControlLabel from "@mui/material/FormControlLabel";
import Slider from "@mui/material/Slider";
import Switch from "@mui/material/Switch";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import CenterFocusStrongOutlinedIcon from "@mui/icons-material/CenterFocusStrongOutlined";
import FitScreenOutlinedIcon from "@mui/icons-material/FitScreenOutlined";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import LinkOffOutlinedIcon from "@mui/icons-material/LinkOffOutlined";
import RestartAltOutlinedIcon from "@mui/icons-material/RestartAltOutlined";
import ZoomOutMapOutlinedIcon from "@mui/icons-material/ZoomOutMapOutlined";

import { CursorIconButton } from "../../common/index.js";

/**
 * @typedef {(key: string, vars?: Record<string, string | number>) => string} TranslateFn
 */

/**
 * @param {{
 *   t: TranslateFn,
 *   layoutMode: string,
 *   repulsionPercent: number,
 *   onRepulsionChange: (v: number) => void,
 *   edgeLabelMode: "all" | "interaction" | "adaptive",
 *   onEdgeLabelModeChange: (mode: "all" | "interaction" | "adaptive") => void,
 *   graphColorBy: "type" | "community",
 *   onGraphColorByChange: (v: "type" | "community") => void,
 *   graphCommunityHulls: boolean,
 *   onGraphCommunityHullsChange: (v: boolean) => void,
 *   onFit: () => void,
 *   onResetZoom: () => void,
 *   onCenterSelection: () => void,
 *   centerSelectionDisabled: boolean,
 *   onRestartForce: () => void,
 *   onUnpinAll: () => void,
 *   unpinDisabled: boolean,
 * }} props
 */
export default function GraphCanvasViewToolbar({
  t,
  layoutMode,
  repulsionPercent,
  onRepulsionChange,
  edgeLabelMode,
  onEdgeLabelModeChange,
  graphColorBy,
  onGraphColorByChange,
  graphCommunityHulls,
  onGraphCommunityHullsChange,
  onFit,
  onResetZoom,
  onCenterSelection,
  centerSelectionDisabled,
  onRestartForce,
  onUnpinAll,
  unpinDisabled,
}) {
  const tk = useTheme().appTokens;
  const sectionSx = {
    fontSize: "0.58rem",
    color: tk.text.faint,
    fontFamily: "monospace",
    letterSpacing: "0.04em",
    lineHeight: 1.1,
    alignSelf: "center",
    mr: 0.35,
    flexShrink: 0,
  };
  const toggleSx = {
    "& .MuiToggleButton-root": {
      fontSize: "0.65rem",
      py: 0.15,
      px: 0.5,
      minWidth: 0,
      textTransform: "none",
      color: tk.text.muted,
      borderColor: tk.border.strong,
    },
    "& .MuiToggleButton-root.Mui-selected": {
      color: tk.accent.fg,
      backgroundColor: tk.accent.chipReadyBg,
    },
  };
  return (
    <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 0.65, px: 1, py: 0.5, borderBottom: `1px solid ${tk.border.default}` }}>
      <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 0.5 }}>
        <Tooltip title={t("graph.canvas.helpTooltip")}>
          <CursorIconButton type="button" aria-label={t("graph.canvas.helpAria")}>
            <InfoOutlinedIcon sx={{ fontSize: "1.05rem" }} />
          </CursorIconButton>
        </Tooltip>
      </Box>
      <Divider orientation="vertical" flexItem sx={{ borderColor: tk.border.default, alignSelf: "stretch", minHeight: 28 }} />
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          gap: 0.35,
          ...(graphColorBy === "community"
            ? {
                px: 0.65,
                py: 0.25,
                borderRadius: "6px",
                border: `1px solid ${tk.accent.softBorder}`,
                backgroundColor: tk.accent.softBg,
              }
            : {}),
        }}
      >
        <Typography component="span" sx={sectionSx}>
          {t("graph.canvas.toolbarSectionColor")}
        </Typography>
        {graphColorBy === "community" ? (
          <Tooltip title={t("graph.canvas.toolbarCommunityModeBadgeTooltip")}>
            <Typography
              component="span"
              sx={{
                fontSize: "0.58rem",
                fontWeight: 600,
                color: tk.accent.fg,
                px: 0.4,
                py: 0.05,
                borderRadius: "4px",
                border: `1px solid ${tk.accent.softBorder}`,
                backgroundColor: tk.accent.chipReadyBg,
                cursor: "help",
                lineHeight: 1.2,
              }}
            >
              {t("graph.canvas.toolbarCommunityModeBadge")}
            </Typography>
          </Tooltip>
        ) : null}
        <ToggleButtonGroup
          size="small"
          value={graphColorBy}
          exclusive
          onChange={(_, v) => v && onGraphColorByChange(v)}
          aria-label={t("graph.community.colorByAria")}
          sx={toggleSx}
        >
          <ToggleButton value="type" title={t("graph.community.colorByTypeTooltip")}>
            {t("graph.community.colorByType")}
          </ToggleButton>
          <ToggleButton value="community" title={t("graph.community.colorByClusterTooltip")}>
            {t("graph.community.colorByCluster")}
          </ToggleButton>
        </ToggleButtonGroup>
        {graphColorBy === "community" ? (
          <Typography sx={{ fontSize: "0.58rem", color: tk.text.faint, maxWidth: 120, lineHeight: 1.25, ml: 0.25 }}>
            {t("graph.canvas.toolbarCommunityFillHint")}
          </Typography>
        ) : null}
        {graphColorBy === "community" ? (
          <Tooltip title={t("graph.community.toggleHullsTooltip")}>
            <FormControlLabel
              sx={{ mr: 0, ml: 0.25, gap: 0.25, "& .MuiFormControlLabel-label": { fontSize: "0.65rem", color: tk.text.muted } }}
              control={
                <Switch
                  size="small"
                  checked={graphCommunityHulls}
                  onChange={(e) => onGraphCommunityHullsChange(e.target.checked)}
                  inputProps={{ "aria-label": t("graph.community.toggleHullsAria") }}
                />
              }
              label={t("graph.community.toggleHulls")}
            />
          </Tooltip>
        ) : null}
      </Box>
      <Divider orientation="vertical" flexItem sx={{ borderColor: tk.border.default, alignSelf: "stretch", minHeight: 28 }} />
      <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 0.35 }}>
        <Typography component="span" sx={sectionSx}>
          {t("graph.canvas.toolbarSectionLabels")}
        </Typography>
        <ToggleButtonGroup
          size="small"
          value={edgeLabelMode}
          exclusive
          onChange={(_, v) => v && onEdgeLabelModeChange(v)}
          aria-label={t("graph.canvas.edgeLabels.modeAria")}
          sx={toggleSx}
        >
          <ToggleButton value="all" title={t("graph.canvas.edgeLabels.tooltipAll")}>
            {t("graph.canvas.edgeLabels.all")}
          </ToggleButton>
          <ToggleButton value="interaction" title={t("graph.canvas.edgeLabels.tooltipInteraction")}>
            {t("graph.canvas.edgeLabels.interaction")}
          </ToggleButton>
          <ToggleButton value="adaptive" title={t("graph.canvas.edgeLabels.tooltipAdaptive")}>
            {t("graph.canvas.edgeLabels.adaptive")}
          </ToggleButton>
        </ToggleButtonGroup>
      </Box>
      <Divider orientation="vertical" flexItem sx={{ borderColor: tk.border.default, alignSelf: "stretch", minHeight: 28 }} />
      <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 0.45 }}>
        <Typography component="span" sx={sectionSx}>
          {t("graph.canvas.toolbarSectionView")}
        </Typography>
        <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 0.5 }}>
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
        {layoutMode === "force" ? (
          <Tooltip title={t("graph.canvas.repulsionTooltip")}>
            <Box sx={{ width: 128, px: 0.25, cursor: "help" }}>
              <Box sx={{ display: "flex", alignItems: "baseline", gap: 0.5, mb: 0.15 }}>
                <Typography sx={{ fontSize: "0.58rem", color: tk.text.faint, fontFamily: "monospace", letterSpacing: "0.02em" }}>
                  sim
                </Typography>
                <Typography sx={{ fontSize: "0.65rem", color: tk.text.muted, flex: 1 }}>
                  {t("graph.canvas.repulsion", { percent: String(Math.round(repulsionPercent)) })}
                </Typography>
              </Box>
              <Slider
                size="small"
                value={repulsionPercent}
                min={0}
                max={100}
                onChange={(_, v) => onRepulsionChange(v)}
                aria-label={t("graph.canvas.repulsionAria")}
              />
            </Box>
          </Tooltip>
        ) : null}
        {layoutMode === "force" ? (
          <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 0.5 }}>
            <Tooltip title={t("graph.canvas.restartForceTooltip")}>
              <CursorIconButton type="button" aria-label={t("graph.canvas.restartForceAria")} onClick={onRestartForce}>
                <RestartAltOutlinedIcon sx={{ fontSize: "1.05rem" }} />
              </CursorIconButton>
            </Tooltip>
            <Tooltip title={t("graph.canvas.unpinAllTooltip")}>
              <CursorIconButton type="button" aria-label={t("graph.canvas.unpinAllAria")} onClick={onUnpinAll} disabled={unpinDisabled}>
                <LinkOffOutlinedIcon sx={{ fontSize: "1.05rem" }} />
              </CursorIconButton>
            </Tooltip>
          </Box>
        ) : null}
      </Box>
      <Box sx={{ flex: 1, minWidth: 8 }} />
    </Box>
  );
}
