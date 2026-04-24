/**
 * @param {string} intlLocale BCP 47 tag from useI18n().intlLocale
 * @param {Date | number} value
 * @param {Intl.DateTimeFormatOptions} options
 */
export function formatUiDateTime(intlLocale, value, options) {
  const d = value instanceof Date ? value : new Date(value);
  return new Intl.DateTimeFormat(intlLocale, options).format(d);
}

/**
 * @param {string} intlLocale
 * @param {number} value
 * @param {Intl.NumberFormatOptions} [options]
 */
export function formatUiNumber(intlLocale, value, options) {
  return new Intl.NumberFormat(intlLocale, options).format(value);
}
