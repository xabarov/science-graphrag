import React, { useMemo } from "react";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

/** @param {import("../../theme/appTokensTypes.js").AppTokens} tk */
function baseButtonSxFromTokens(tk) {
  return {
    textTransform: "none",
    fontWeight: 500,
    fontSize: "0.8125rem",
    borderRadius: 6,
    transition: "all 0.15s ease",
    border: `1px solid ${tk.border.strong}`,
    background: tk.control.outlinedBg,
    color: tk.text.primary,
    "&:hover": {
      background: tk.control.outlinedBgHover,
      borderColor: tk.control.outlinedBorderHover,
    },
    "&:active": {
      transform: "scale(0.98)",
    },
  };
}

export function CursorButton({ sx, ...props }) {
  const tk = useTheme().appTokens;
  const base = useMemo(() => baseButtonSxFromTokens(tk), [tk]);
  return <Button variant="outlined" sx={{ ...base, ...(sx || {}) }} {...props} />;
}

export function CursorPrimaryButton({ sx, ...props }) {
  const tk = useTheme().appTokens;
  const primarySx = useMemo(
    () => ({
      ...baseButtonSxFromTokens(tk),
      background: tk.accent.softBg,
      borderColor: tk.accent.softBorder,
      color: tk.accent.fg,
      "&:hover": {
        background: tk.accent.emphasisHoverBg,
        borderColor: tk.accent.emphasisHoverBorder,
      },
    }),
    [tk],
  );
  return <Button variant="outlined" sx={{ ...primarySx, ...(sx || {}) }} {...props} />;
}

export function CursorDangerButton({ sx, ...props }) {
  const tk = useTheme().appTokens;
  const dangerSx = useMemo(
    () => ({
      ...baseButtonSxFromTokens(tk),
      color: tk.state.dangerFg,
      borderColor: tk.state.dangerBorder,
      background: "transparent",
      "&:hover": {
        background: tk.state.dangerBg,
        borderColor: tk.state.dangerHoverBorder,
      },
    }),
    [tk],
  );
  return <Button variant="outlined" sx={{ ...dangerSx, ...(sx || {}) }} {...props} />;
}

export function CursorIconButton({ sx, children, ...props }) {
  const tk = useTheme().appTokens;
  const iconSx = useMemo(
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
  return (
    <IconButton size="small" sx={{ ...iconSx, ...(sx || {}) }} {...props}>
      {children}
    </IconButton>
  );
}

export function CursorSmallButton({ children, sx, ...props }) {
  const tk = useTheme().appTokens;
  const base = useMemo(() => baseButtonSxFromTokens(tk), [tk]);
  return (
    <Button
      variant="outlined"
      sx={{
        ...base,
        fontSize: "0.75rem",
        padding: "4px 10px",
        minHeight: 28,
        ...(sx || {}),
      }}
      {...props}
    >
      <Typography component="span" sx={{ fontSize: "inherit" }}>
        {children}
      </Typography>
    </Button>
  );
}

export { default as CursorIconAction } from "./CursorIconAction.jsx";
export { default as CopyIdButton } from "./CopyIdButton.jsx";
