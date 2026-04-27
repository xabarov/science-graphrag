import { createTheme } from "@mui/material/styles";

/** @typedef {import("./appTokensTypes.js").AppTokens} AppTokens */

/**
 * Semantic tokens. Baseline table: docs/analysis/light-theme-roadmap-2026-04-27.md §10.6.
 */

/** @type {AppTokens} */
const DARK_TOKENS = {
  surface: {
    app: "#0a0a0a",
    sidebar: "#141414",
    panel: "#1a1a1a",
    panelAlt: "#1a1a1a",
    code: "#0a0a0a",
    subtle: "rgba(255,255,255,0.04)",
  },
  border: {
    default: "rgba(255,255,255,0.08)",
    strong: "rgba(255,255,255,0.12)",
  },
  text: {
    primary: "rgba(255,255,255,0.9)",
    secondary: "rgba(255,255,255,0.6)",
    muted: "rgba(255,255,255,0.45)",
    accent: "rgba(129,140,248,0.95)",
    faint: "rgba(255,255,255,0.28)",
  },
  accent: {
    softBg: "rgba(99,102,241,0.15)",
    softBorder: "rgba(99,102,241,0.3)",
    fg: "rgba(129,140,248,0.95)",
    emphasisHoverBg: "rgba(99,102,241,0.2)",
    emphasisHoverBorder: "rgba(99,102,241,0.42)",
    chipReadyBg: "rgba(99,102,241,0.12)",
    chipReadyFg: "rgba(129,140,248,0.95)",
  },
  state: {
    dangerFg: "rgba(239,68,68,0.8)",
    dangerBg: "rgba(239,68,68,0.08)",
    dangerBorder: "rgba(239,68,68,0.2)",
    dangerHoverBorder: "rgba(239,68,68,0.28)",
  },
  control: {
    outlinedBg: "rgba(255,255,255,0.02)",
    outlinedBgHover: "rgba(255,255,255,0.06)",
    outlinedBorderHover: "rgba(255,255,255,0.18)",
    navItemHoverBg: "rgba(255,255,255,0.04)",
    chipMutedBg: "rgba(255,255,255,0.06)",
    chipMutedFg: "rgba(255,255,255,0.55)",
  },
};

/** @type {AppTokens} */
const LIGHT_TOKENS = {
  surface: {
    app: "#f5f7fb",
    sidebar: "#eef2f7",
    panel: "#ffffff",
    panelAlt: "#f8fafc",
    code: "#f1f5f9",
    subtle: "rgba(15,23,42,0.05)",
  },
  border: {
    default: "rgba(15,23,42,0.10)",
    strong: "rgba(15,23,42,0.14)",
  },
  text: {
    primary: "rgba(15,23,42,0.92)",
    secondary: "rgba(15,23,42,0.62)",
    muted: "rgba(15,23,42,0.48)",
    accent: "rgba(79,70,229,0.88)",
    faint: "rgba(15,23,42,0.38)",
  },
  accent: {
    softBg: "rgba(99,102,241,0.10)",
    softBorder: "rgba(99,102,241,0.22)",
    fg: "rgba(79,70,229,0.88)",
    emphasisHoverBg: "rgba(99,102,241,0.14)",
    emphasisHoverBorder: "rgba(99,102,241,0.32)",
    chipReadyBg: "rgba(99,102,241,0.10)",
    chipReadyFg: "rgba(79,70,229,0.88)",
  },
  state: {
    dangerFg: "rgba(185,28,28,0.92)",
    dangerBg: "rgba(239,68,68,0.08)",
    dangerBorder: "rgba(239,68,68,0.22)",
    dangerHoverBorder: "rgba(239,68,68,0.32)",
  },
  control: {
    outlinedBg: "rgba(15,23,42,0.03)",
    outlinedBgHover: "rgba(15,23,42,0.07)",
    outlinedBorderHover: "rgba(15,23,42,0.22)",
    navItemHoverBg: "rgba(15,23,42,0.05)",
    chipMutedBg: "rgba(15,23,42,0.06)",
    chipMutedFg: "rgba(15,23,42,0.55)",
  },
};

/** Default tokens for pure helpers outside React (e.g. chip `sx` factories). */
export const APP_TOKENS_FALLBACK_DARK = DARK_TOKENS;
export const APP_TOKENS_FALLBACK_LIGHT = LIGHT_TOKENS;

/**
 * @param {"dark"|"light"} effectiveMode
 */
export function buildAppTheme(effectiveMode) {
  const mode = effectiveMode === "light" ? "light" : "dark";
  /** @type {AppTokens} */
  const appTokens = mode === "light" ? LIGHT_TOKENS : DARK_TOKENS;

  return createTheme({
    palette: {
      mode,
      background: {
        default: appTokens.surface.app,
        paper: appTokens.surface.panel,
      },
      text: {
        primary: appTokens.text.primary,
        secondary: appTokens.text.secondary,
      },
    },
    typography: {
      fontFamily: 'Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      fontSize: 13,
    },
    appTokens,
  });
}
