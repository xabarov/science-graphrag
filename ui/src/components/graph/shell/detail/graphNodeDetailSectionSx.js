/**
 * Shared MUI `sx` fragments for graph node detail panels (no React).
 *
 * @param {import("@mui/material/styles").Theme["appTokens"]} tk
 */

/** @param {boolean} compact */
export function graphDetailClaimBodySx(tk, compact) {
  return {
    fontSize: "0.8125rem",
    color: tk.text.primary,
    lineHeight: 1.45,
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
    p: 1,
    borderRadius: "6px",
    border: `1px solid ${tk.border.default}`,
    backgroundColor: tk.surface.sidebar,
    maxHeight: compact ? 220 : 320,
    overflow: "auto",
  };
}

/** @param {boolean} compact */
export function graphDetailMarkdownPanelSx(tk, compact) {
  return {
    p: 1,
    borderRadius: "6px",
    border: `1px solid ${tk.border.default}`,
    backgroundColor: tk.surface.sidebar,
    maxHeight: compact ? 260 : 360,
    overflow: "auto",
  };
}

/** @param {boolean} compact */
export function graphDetailCodePreSx(tk, compact) {
  return {
    m: 0,
    p: 1.25,
    borderRadius: "6px",
    backgroundColor: tk.surface.code,
    border: `1px solid ${tk.border.default}`,
    fontSize: "0.72rem",
    color: tk.text.secondary,
    overflow: "auto",
    maxHeight: compact ? 200 : 280,
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
  };
}
