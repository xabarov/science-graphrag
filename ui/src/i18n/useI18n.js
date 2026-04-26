import { useContext } from "react";

import { I18nContext } from "./I18nContextInstance.js";

/** @returns {import("./I18nContextInstance.js").I18nValue} */
export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    throw new Error("useI18n must be used within I18nProvider");
  }
  return ctx;
}
