import React, { useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Divider from "@mui/material/Divider";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import Popover from "@mui/material/Popover";
import Radio from "@mui/material/Radio";
import RadioGroup from "@mui/material/RadioGroup";
import Switch from "@mui/material/Switch";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import LabelOutlinedIcon from "@mui/icons-material/LabelOutlined";

import { CursorIconButton } from "../../common/index.js";

const CANVAS_LABEL_MODE_DEFAULT = "adaptive";
const HOVER_NEIGHBORS_LABELS_DEFAULT = true;

/**
 * @typedef {(key: string, vars?: Record<string, string | number>) => string} TranslateFn
 */

/**
 * Popover + trigger for canvas label mode and neighbor labels on hover.
 *
 * @param {{
 *   t: TranslateFn,
 *   canvasLabelMode: "all" | "interaction" | "adaptive",
 *   onCanvasLabelModeChange: (mode: "all" | "interaction" | "adaptive") => void,
 *   hoverNeighborsLabels: boolean,
 *   onHoverNeighborsLabelsChange: (v: boolean) => void,
 * }} props
 */
export default function GraphCanvasLabelsControl({
  t,
  canvasLabelMode,
  onCanvasLabelModeChange,
  hoverNeighborsLabels,
  onHoverNeighborsLabelsChange,
}) {
  const tk = useTheme().appTokens;
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
    <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 0.35 }}>
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
          <RadioGroup aria-label={t("graph.canvasLabels.modeAria")} name="canvas-labels-mode" value={canvasLabelMode} onChange={handleLabelsModeRadio}>
            <FormControlLabel
              value="all"
              control={<Radio size="small" />}
              label={
                <Box sx={{ display: "flex", flexDirection: "column" }}>
                  <Typography sx={{ fontSize: "0.75rem", color: tk.text.primary }}>{t("graph.canvasLabels.modeAll")}</Typography>
                  <Typography sx={{ fontSize: "0.62rem", color: tk.text.faint }}>{t("graph.canvasLabels.tooltipAll")}</Typography>
                </Box>
              }
              sx={{ alignItems: "flex-start", mb: 0.4 }}
            />
            <FormControlLabel
              value="interaction"
              control={<Radio size="small" />}
              label={
                <Box sx={{ display: "flex", flexDirection: "column" }}>
                  <Typography sx={{ fontSize: "0.75rem", color: tk.text.primary }}>{t("graph.canvasLabels.modeInteraction")}</Typography>
                  <Typography sx={{ fontSize: "0.62rem", color: tk.text.faint }}>{t("graph.canvasLabels.tooltipInteraction")}</Typography>
                </Box>
              }
              sx={{ alignItems: "flex-start", mb: 0.4 }}
            />
            <FormControlLabel
              value="adaptive"
              control={<Radio size="small" />}
              label={
                <Box sx={{ display: "flex", flexDirection: "column" }}>
                  <Typography sx={{ fontSize: "0.75rem", color: tk.text.primary }}>{t("graph.canvasLabels.modeAdaptive")}</Typography>
                  <Typography sx={{ fontSize: "0.62rem", color: tk.text.faint }}>{t("graph.canvasLabels.tooltipAdaptive")}</Typography>
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
  );
}
