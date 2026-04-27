import React, { useMemo } from "react";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import CircularProgress from "@mui/material/CircularProgress";
import Tooltip from "@mui/material/Tooltip";
import { useTheme } from "@mui/material/styles";

/**
 * Icon button with tooltip. Supports Router Link via `component` + `to`.
 *
 * @param {{
 *   title: string,
 *   children: React.ReactNode,
 *   busy?: boolean,
 *   disabled?: boolean,
 *   onClick?: (e: React.MouseEvent) => void,
 *   component?: React.ElementType,
 *   to?: string,
 *   sx?: object,
 *   "aria-label"?: string,
 * }} props
 */
export default function CursorIconAction({ title, children, busy, disabled, onClick, component, to, sx, "aria-label": ariaLabel, ...rest }) {
  const tk = useTheme().appTokens;
  const iconButtonSx = useMemo(
    () => ({
      padding: "6px",
      borderRadius: 6,
      border: `1px solid ${tk.border.strong}`,
      color: tk.text.secondary,
      transition: "all 0.15s ease",
      "&:hover": {
        background: tk.control.outlinedBgHover,
        color: tk.text.primary,
      },
      "&:active": {
        transform: "scale(0.98)",
      },
    }),
    [tk],
  );

  const btn = (
    <IconButton
      component={component}
      to={to}
      size="small"
      disabled={Boolean(disabled || busy)}
      onClick={onClick}
      aria-label={ariaLabel || title}
      sx={{ ...iconButtonSx, ...(sx || {}) }}
      {...rest}
    >
      {busy ? <CircularProgress size={14} sx={{ color: tk.accent.fg }} /> : children}
    </IconButton>
  );
  return (
    <Tooltip title={title} arrow placement="bottom">
      <Box component="span" sx={{ display: "inline-flex", verticalAlign: "middle" }}>
        {btn}
      </Box>
    </Tooltip>
  );
}
