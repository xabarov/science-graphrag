import { useContext } from "react";

import { AppearanceContext } from "./appearanceContext.jsx";

export function useAppearance() {
  const ctx = useContext(AppearanceContext);
  if (!ctx) {
    throw new Error("useAppearance must be used within AppearanceProvider");
  }
  return ctx;
}
