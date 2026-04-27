import { useTheme } from "@mui/material/styles";

/**
 * Semantic app colors from the active MUI theme (`theme.appTokens`).
 * Prefer this over duplicating hex/rgba literals in `sx`.
 *
 * @returns {import("./appTokensTypes.js").AppTokens}
 */
export function useAppTokens() {
  const theme = useTheme();
  return theme.appTokens;
}
