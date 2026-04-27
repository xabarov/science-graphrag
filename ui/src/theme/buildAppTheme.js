import { createTheme } from "@mui/material/styles";

/**
 * Semantic tokens (LT1 minimal set). See docs/analysis/light-theme-roadmap-2026-04-27.md §10.6.
 *
 * @typedef {{
 *   surface: { app: string, sidebar: string, panel: string, panelAlt: string, code: string },
 *   border: { default: string, strong: string },
 *   text: { primary: string, secondary: string, muted: string, accent: string },
 *   accent: { softBg: string, softBorder: string, fg: string },
 *   state: { dangerFg: string, dangerBg: string, dangerBorder: string },
 * }} AppTokens
 */

/** @type {AppTokens} */
const DARK_TOKENS = {
  surface: {
    app: "#0a0a0a",
    sidebar: "#141414",
    panel: "#1a1a1a",
    panelAlt: "#1a1a1a",
    code: "#0a0a0a",
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
  },
  accent: {
    softBg: "rgba(99,102,241,0.15)",
    softBorder: "rgba(99,102,241,0.3)",
    fg: "rgba(129,140,248,0.95)",
  },
  state: {
    dangerFg: "rgba(239,68,68,0.8)",
    dangerBg: "rgba(239,68,68,0.08)",
    dangerBorder: "rgba(239,68,68,0.2)",
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
  },
  accent: {
    softBg: "rgba(99,102,241,0.10)",
    softBorder: "rgba(99,102,241,0.22)",
    fg: "rgba(79,70,229,0.88)",
  },
  state: {
    dangerFg: "rgba(185,28,28,0.92)",
    dangerBg: "rgba(239,68,68,0.08)",
    dangerBorder: "rgba(239,68,68,0.22)",
  },
};

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
