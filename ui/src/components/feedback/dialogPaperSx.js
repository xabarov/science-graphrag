/**
 * @param {import("@mui/material/styles").Theme} theme
 * @returns {import("@mui/material/styles").SxProps<import("@mui/material/styles").Theme>}
 */
export function feedbackDialogPaperSx(theme) {
  const tk = theme.appTokens;
  return {
    backgroundColor: tk.surface.panel,
    border: `1px solid ${tk.border.default}`,
    borderRadius: "6px",
  };
}
