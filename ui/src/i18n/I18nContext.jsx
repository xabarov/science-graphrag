import { useCallback, useEffect, useMemo, useState } from "react";

import {
  DEFAULT_LOCALE,
  I18N_STORAGE_KEY,
  SUPPORTED_LOCALES,
  htmlLangFor,
  intlLocaleFor,
} from "./constants.js";
import { I18nContext } from "./I18nContextInstance.js";
import { readStoredLocale } from "./readStoredLocale.js";
import { setRuntimeIntlLocale } from "./runtimeIntlLocale.js";
import { translate } from "./translate.js";

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
