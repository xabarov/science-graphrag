import React, { useCallback, useEffect, useLayoutEffect, useMemo, useState } from "react";
import { ThemeProvider } from "@mui/material/styles";

import { AppearanceContext } from "./appearanceContext.jsx";
import {
  applyDocumentColorScheme,
  readAppearancePreference,
  resolveEffectiveAppearanceMode,
  writeAppearancePreference,
} from "./appearanceMode.js";
import { buildAppTheme } from "./buildAppTheme.js";

/**
 * Owns appearance preference, resolves effective light/dark, syncs `document.documentElement`, and provides MUI theme.
 *
 * @param {{ children: import("react").ReactNode }} props
 */
export function AppearanceProvider({ children }) {
  const [preference, setPreferenceState] = useState(() => readAppearancePreference());
  const [effective, setEffective] = useState(() => resolveEffectiveAppearanceMode(readAppearancePreference()));

  useLayoutEffect(() => {
    applyDocumentColorScheme(effective);
  }, [effective]);

  useEffect(() => {
    if (preference !== "system") return undefined;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      setEffective(resolveEffectiveAppearanceMode("system", mq.matches));
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [preference]);

  const setPreference = useCallback((next) => {
    const normalized = writeAppearancePreference(next);
    setPreferenceState(normalized);
    setEffective(resolveEffectiveAppearanceMode(normalized));
  }, []);

  const theme = useMemo(() => buildAppTheme(effective), [effective]);

  const value = useMemo(
    () => ({
      preference,
      effective,
      setPreference,
    }),
    [preference, effective, setPreference],
  );

  return (
    <AppearanceContext.Provider value={value}>
      <ThemeProvider theme={theme}>{children}</ThemeProvider>
    </AppearanceContext.Provider>
  );
}
