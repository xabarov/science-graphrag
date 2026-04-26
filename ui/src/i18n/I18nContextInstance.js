import { createContext } from "react";

/** @typedef {import("./constants.js").UiLocale} UiLocale */

/**
 * @typedef {{
 *   locale: UiLocale,
 *   setLocale: (next: UiLocale) => void,
 *   t: (key: string, vars?: Record<string, string | number>) => string,
 *   intlLocale: string,
 * }} I18nValue
 */

/** @type {import("react").Context<I18nValue | null>} */
export const I18nContext = createContext(null);
