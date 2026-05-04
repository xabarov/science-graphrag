import React, { useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Divider from "@mui/material/Divider";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import Popover from "@mui/material/Popover";
import Radio from "@mui/material/Radio";
import RadioGroup from "@mui/material/RadioGroup";
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
import LabelOutlinedIcon from "@mui/icons-material/LabelOutlined";
import LinkOffOutlinedIcon from "@mui/icons-material/LinkOffOutlined";
import RestartAltOutlinedIcon from "@mui/icons-material/RestartAltOutlined";
import ZoomOutMapOutlinedIcon from "@mui/icons-material/ZoomOutMapOutlined";

import { CursorIconButton } from "../../common/index.js";

const CANVAS_LABEL_MODE_DEFAULT = "adaptive";
const HOVER_NEIGHBORS_LABELS_DEFAULT = true;

/**
 * @typedef {(key: string, vars?: Record<string, string | number>) => string} TranslateFn
 */

/**
 * @param {{
 *   t: TranslateFn,
 *   layoutMode: string,
 *   repulsionPercent: number,
 *   onRepulsionChange: (v: number) => void,
 *   canvasLabelMode: "all" | "interaction" | "adaptive",
 *   onCanvasLabelModeChange: (mode: "all" | "interaction" | "adaptive") => void,
 *   hoverNeighborsLabels: boolean,
 *   onHoverNeighborsLabelsChange: (v: boolean) => void,
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
  canvasLabelMode,
  onCanvasLabelModeChange,
  hoverNeighborsLabels,
  onHoverNeighborsLabelsChange,
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

  const [labelsAnchorEl, setLabelsAnchorEl] = useState(/** @type {HTMLElement | null} */ (null));
  const [labelsPopoverOpen, setLabelsPopoverOpen] = useState(false);
  const openLabelsPopover = (event) => {
    setLabelsAnchorEl(event.currentTarget);
    setLabelsPopoverOpen(true);
  };
  const closeLabelsPopover = () => {
    setLabelsPopoverOpen(false);
    setLabelsAnchorEl(null);
  };
  const handleLabelsModeRadio = (event) => {
    const v = event.target.value;
    if (v === "all" || v === "interaction" || v === "adaptive") {
      onCanvasLabelModeChange(v);
    }
  };
  const handleNeighborsToggle = (event) => {
    onHoverNeighborsLabelsChange(Boolean(event.target.checked));
  };
  const handleLabelsReset = () => {
    onCanvasLabelModeChange(CANVAS_LABEL_MODE_DEFAULT);
    onHoverNeighborsLabelsChange(HOVER_NEIGHBORS_LABELS_DEFAULT);
  };
  const labelsModeBadge =
    canvasLabelMode === "all"
      ? t("graph.canvasLabels.modeAll")
      : canvasLabelMode === "interaction"
        ? t("graph.canvasLabels.modeInteraction")
        : t("graph.canvasLabels.modeAdaptive");
  const neighborsToggleEnabled = canvasLabelMode === "interaction" || canvasLabelMode === "adaptive";
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
        <Box sx={{ display: "inline-flex" }}>
          <Tooltip title={t("graph.canvasLabels.buttonTooltip", { mode: labelsModeBadge })}>
            <CursorIconButton
              type="button"
              aria-label={t("graph.canvasLabels.buttonAria")}
              aria-haspopup="true"
              aria-expanded={labelsPopoverOpen ? "true" : "false"}
              onClick={openLabelsPopover}
              sx={{
                gap: 0.4,
                px: 0.6,
                display: "inline-flex",
                alignItems: "center",
              }}
            >
              <LabelOutlinedIcon sx={{ fontSize: "1.05rem" }} />
              <Typography
                component="span"
                sx={{
                  fontSize: "0.65rem",
                  color: tk.text.muted,
                  lineHeight: 1.1,
                }}
              >
                {labelsModeBadge}
              </Typography>
            </CursorIconButton>
          </Tooltip>
        </Box>
        <Popover
          open={labelsPopoverOpen}
          anchorEl={labelsAnchorEl}
          onClose={closeLabelsPopover}
          anchorOrigin={{ vertical: "bottom", horizontal: "left" }}
          transformOrigin={{ vertical: "top", horizontal: "left" }}
          slotProps={{
            paper: {
              sx: {
                p: 1.25,
                width: 264,
                backgroundColor: tk.surface.panel,
                border: `1px solid ${tk.border.default}`,
              },
            },
          }}
        >
          <Typography sx={{ fontSize: "0.72rem", fontWeight: 600, color: tk.text.primary, mb: 0.5 }}>
            {t("graph.canvasLabels.popoverTitle")}
          </Typography>
          <Typography sx={{ fontSize: "0.65rem", color: tk.text.faint, mb: 1, lineHeight: 1.35 }}>
            {t("graph.canvasLabels.popoverDescription")}
          </Typography>
          <FormControl component="fieldset">
            <RadioGroup
              aria-label={t("graph.canvasLabels.modeAria")}
              name="canvas-labels-mode"
              value={canvasLabelMode}
              onChange={handleLabelsModeRadio}
            >
              <FormControlLabel
                value="all"
                control={<Radio size="small" />}
                label={
                  <Box sx={{ display: "flex", flexDirection: "column" }}>
                    <Typography sx={{ fontSize: "0.75rem", color: tk.text.primary }}>
                      {t("graph.canvasLabels.modeAll")}
                    </Typography>
                    <Typography sx={{ fontSize: "0.62rem", color: tk.text.faint }}>
                      {t("graph.canvasLabels.tooltipAll")}
                    </Typography>
                  </Box>
                }
                sx={{ alignItems: "flex-start", mb: 0.4 }}
              />
              <FormControlLabel
                value="interaction"
                control={<Radio size="small" />}
                label={
                  <Box sx={{ display: "flex", flexDirection: "column" }}>
                    <Typography sx={{ fontSize: "0.75rem", color: tk.text.primary }}>
                      {t("graph.canvasLabels.modeInteraction")}
                    </Typography>
                    <Typography sx={{ fontSize: "0.62rem", color: tk.text.faint }}>
                      {t("graph.canvasLabels.tooltipInteraction")}
                    </Typography>
                  </Box>
                }
                sx={{ alignItems: "flex-start", mb: 0.4 }}
              />
              <FormControlLabel
                value="adaptive"
                control={<Radio size="small" />}
                label={
                  <Box sx={{ display: "flex", flexDirection: "column" }}>
                    <Typography sx={{ fontSize: "0.75rem", color: tk.text.primary }}>
                      {t("graph.canvasLabels.modeAdaptive")}
                    </Typography>
                    <Typography sx={{ fontSize: "0.62rem", color: tk.text.faint }}>
                      {t("graph.canvasLabels.tooltipAdaptive")}
                    </Typography>
                  </Box>
                }
                sx={{ alignItems: "flex-start", mb: 0.6 }}
              />
            </RadioGroup>
          </FormControl>
          <Divider sx={{ my: 0.75, borderColor: tk.border.default }} />
          <Tooltip title={t("graph.canvasLabels.neighborsTooltip")}>
            <FormControlLabel
              sx={{
                ml: 0,
                gap: 0.5,
                "& .MuiFormControlLabel-label": { fontSize: "0.72rem", color: tk.text.primary },
              }}
              disabled={!neighborsToggleEnabled}
              control={
                <Switch
                  size="small"
                  checked={Boolean(hoverNeighborsLabels)}
                  onChange={handleNeighborsToggle}
                  inputProps={{ "aria-label": t("graph.canvasLabels.neighborsToggle") }}
                />
              }
              label={t("graph.canvasLabels.neighborsToggle")}
            />
          </Tooltip>
          <Box sx={{ display: "flex", justifyContent: "flex-end", mt: 0.75 }}>
            <Button
              type="button"
              size="small"
              onClick={handleLabelsReset}
              sx={{ fontSize: "0.65rem", textTransform: "none", color: tk.text.muted, minWidth: 0 }}
            >
              {t("graph.canvasLabels.reset")}
            </Button>
          </Box>
        </Popover>
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
