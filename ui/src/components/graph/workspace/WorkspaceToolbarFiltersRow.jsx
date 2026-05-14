import React from "react";
import ClearIcon from "@mui/icons-material/Clear";
import MyLocationOutlinedIcon from "@mui/icons-material/MyLocationOutlined";
import Divider from "@mui/material/Divider";
import IconButton from "@mui/material/IconButton";
import InputAdornment from "@mui/material/InputAdornment";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";

import { CursorIconButton } from "../../common/index.js";
import GraphNodesVisibilityMenu from "../toolbar/GraphNodesVisibilityMenu.jsx";

/**
 * Filters zone: optional leading slot, visibility menu, local find + focus-first.
 *
 * @param {{
 *   leadingSlot?: import("react").ReactNode,
 *   dividerSx: object,
 *   nodesMenuEnabled: boolean,
 *   visibility: import("../model/graphVisibilityFilter.js").GraphVisibilityValue,
 *   onVisibilityChange: (patch: Partial<import("../model/graphVisibilityFilter.js").GraphVisibilityValue>) => void,
 *   t: (k: string, opts?: object) => string,
 *   canvasMode: boolean,
 *   onLocalFindChange?: (ev: import("react").ChangeEvent<HTMLInputElement>) => void,
 *   localFindQuery: string,
 *   onLocalFindClear?: () => void,
 *   onFocusFirstMatch?: () => void,
 *   localFindFocusDisabled: boolean,
 *   localFindFieldSx: object,
 *   tk: import("@mui/material/styles").Theme["appTokens"],
 *   useCompactToolbarRow: boolean,
 *   panelsRow: import("react").ReactNode,
 * }} props
 */
export default function WorkspaceToolbarFiltersRow({
  leadingSlot,
  dividerSx,
  nodesMenuEnabled,
  visibility,
  onVisibilityChange,
  t,
  canvasMode,
  onLocalFindChange,
  localFindQuery,
  onLocalFindClear,
  onFocusFirstMatch,
  localFindFocusDisabled,
  localFindFieldSx,
  tk,
  useCompactToolbarRow,
  panelsRow,
}) {
  return (
    <Stack
      direction="row"
      flexWrap="wrap"
      alignItems="center"
      gap={useCompactToolbarRow ? 0.5 : 1}
      useFlexGap
      aria-label={useCompactToolbarRow ? t("graph.wsToolbar.compactToolbarAria") : undefined}
    >
      {leadingSlot ? (
        <>
          {leadingSlot}
          <Divider orientation="vertical" flexItem sx={dividerSx} />
        </>
      ) : null}
      {nodesMenuEnabled ? (
        <>
          <GraphNodesVisibilityMenu visibility={visibility} onChange={onVisibilityChange} t={t} />
          {canvasMode && onLocalFindChange ? <Divider orientation="vertical" flexItem sx={dividerSx} /> : null}
        </>
      ) : null}

      {canvasMode && onLocalFindChange ? (
        <>
          <TextField
            size="small"
            variant="outlined"
            value={localFindQuery}
            onChange={onLocalFindChange}
            placeholder={t("graph.localFind.placeholder")}
            inputProps={{ "aria-label": t("graph.localFind.aria") }}
            sx={localFindFieldSx}
            InputProps={{
              endAdornment: localFindQuery && onLocalFindClear ? (
                <InputAdornment position="end">
                  <IconButton
                    size="small"
                    aria-label={t("graph.localFind.clearAria")}
                    onClick={onLocalFindClear}
                    edge="end"
                    sx={{ color: tk.text.muted }}
                  >
                    <ClearIcon fontSize="small" />
                  </IconButton>
                </InputAdornment>
              ) : null,
            }}
          />
          {onFocusFirstMatch ? (
            <Tooltip title={t("graph.localFind.focusFirstTooltip")}>
              <span>
                <CursorIconButton
                  type="button"
                  aria-label={t("graph.localFind.focusFirst")}
                  onClick={onFocusFirstMatch}
                  disabled={localFindFocusDisabled}
                >
                  <MyLocationOutlinedIcon sx={{ fontSize: "1.05rem" }} />
                </CursorIconButton>
              </span>
            </Tooltip>
          ) : null}
        </>
      ) : null}

      {useCompactToolbarRow ? (
        <>
          {nodesMenuEnabled || canvasMode ? <Divider orientation="vertical" flexItem sx={dividerSx} /> : null}
          {panelsRow}
        </>
      ) : null}
    </Stack>
  );
}
