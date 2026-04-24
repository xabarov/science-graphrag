import { DEFAULT_LOCALE, I18N_STORAGE_KEY, SUPPORTED_LOCALES } from "./constants.js";

/** @returns {import("./constants.js").UiLocale} */
export function readStoredLocale() {
  try {
    const raw = window.localStorage.getItem(I18N_STORAGE_KEY);
    if (raw && SUPPORTED_LOCALES.includes(raw)) {
      return /** @type {import("./constants.js").UiLocale} */ (raw);
    }
  } catch {
    // ignore
  }
  return DEFAULT_LOCALE;
}
