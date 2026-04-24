/** Synced from I18nProvider for non-React modules (Intl, sorts). Default matches en-US. */
let current = "en-US";

export function setRuntimeIntlLocale(bcp47) {
  current = bcp47 && typeof bcp47 === "string" ? bcp47 : "en-US";
}

export function getRuntimeIntlLocale() {
  return current;
}
