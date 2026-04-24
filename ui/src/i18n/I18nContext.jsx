import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import {
  DEFAULT_LOCALE,
  I18N_STORAGE_KEY,
  SUPPORTED_LOCALES,
  htmlLangFor,
  intlLocaleFor,
} from "./constants.js";
import { readStoredLocale } from "./readStoredLocale.js";
import { setRuntimeIntlLocale } from "./runtimeIntlLocale.js";
import { translate } from "./translate.js";

/** @typedef {import("./constants.js").UiLocale} UiLocale */

/**
 * @typedef {{
 *   locale: UiLocale,
 *   setLocale: (next: UiLocale) => void,
 *   t: (key: string, vars?: Record<string, string | number>) => string,
 *   intlLocale: string,
 * }} I18nValue
 */

/** @type {React.Context<I18nValue | null>} */
const I18nContext = createContext(null);

export function I18nProvider({ children }) {
  const [locale, setLocaleState] = useState(() => {
    if (typeof window === "undefined") return DEFAULT_LOCALE;
    return readStoredLocale();
  });

  useEffect(() => {
    document.documentElement.lang = htmlLangFor(locale);
    try {
      window.localStorage.setItem(I18N_STORAGE_KEY, locale);
    } catch {
      // ignore
    }
  }, [locale]);

  const setLocale = useCallback((next) => {
    if (SUPPORTED_LOCALES.includes(next)) {
      setLocaleState(next);
    }
  }, []);

  const t = useCallback(
    (key, vars) => {
      return translate(key, locale, vars);
    },
    [locale],
  );

  const intlLocale = useMemo(() => intlLocaleFor(locale), [locale]);

  useEffect(() => {
    setRuntimeIntlLocale(intlLocale);
  }, [intlLocale]);

  const value = useMemo(() => ({ locale, setLocale, t, intlLocale }), [locale, setLocale, t, intlLocale]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

/** @returns {I18nValue} */
export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    throw new Error("useI18n must be used within I18nProvider");
  }
  return ctx;
}
