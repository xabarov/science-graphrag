/** @typedef {"en" | "ru"} UiLocale */

export const I18N_STORAGE_KEY = "science-graphrag.ui.locale";

/** @type {UiLocale} */
export const DEFAULT_LOCALE = "en";

/** @type {UiLocale[]} */
export const SUPPORTED_LOCALES = ["en", "ru"];

/** BCP 47 tag for Intl APIs */
export function intlLocaleFor(uiLocale) {
  return uiLocale === "ru" ? "ru-RU" : "en-US";
}

/** HTML lang attribute */
export function htmlLangFor(uiLocale) {
  return uiLocale === "ru" ? "ru" : "en";
}
