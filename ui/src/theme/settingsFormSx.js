/** @typedef {import("./appTokensTypes.js").AppTokens} AppTokens */

/**
 * Outlined TextField tuned for app surfaces (settings, feedback prompt).
 *
 * @param {AppTokens} tk
 */
export function outlinedAppTextFieldSx(tk) {
  return {
    "& .MuiInputBase-root": {
      fontSize: "0.8125rem",
      backgroundColor: tk.control.outlinedBg,
    },
    "& .MuiOutlinedInput-notchedOutline": {
      borderColor: tk.border.strong,
    },
    "& .MuiInputBase-root:hover .MuiOutlinedInput-notchedOutline": {
      borderColor: tk.control.outlinedBorderHover,
    },
    "& .MuiInputBase-root.Mui-focused .MuiOutlinedInput-notchedOutline": {
      borderColor: "rgba(99, 102, 241, 0.5)",
    },
    "& .MuiInputLabel-root": {
      fontSize: "0.8125rem",
      color: tk.text.secondary,
    },
    "& .MuiFormHelperText-root": {
      fontSize: "0.75rem",
      color: tk.text.muted,
    },
  };
}

/**
 * Card-style panel for settings sections.
 *
 * @param {AppTokens} tk
 */
export function settingsCardSx(tk) {
  return {
    border: `1px solid ${tk.border.default}`,
    backgroundColor: tk.surface.panel,
    borderRadius: 1.5,
  };
}

/**
 * Muted Alert surface (keeps severity icon; body uses token text).
 *
 * @param {AppTokens} tk
 */
export function settingsAlertMutedSx(tk) {
  return {
    backgroundColor: tk.surface.subtle,
    border: `1px solid ${tk.border.default}`,
    color: tk.text.primary,
    "& .MuiAlert-icon": { color: "inherit" },
  };
}

/**
 * Nested inset block (e.g. toggle group).
 *
 * @param {AppTokens} tk
 */
export function settingsNestedInsetSx(tk) {
  return {
    border: `1px solid ${tk.border.default}`,
    backgroundColor: tk.control.outlinedBg,
    borderRadius: 1.5,
  };
}
