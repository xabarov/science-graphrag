import en from "./messages/en/index.js";
import ru from "./messages/ru/index.js";

const DICTS = { en, ru };

/**
 * @param {string} key
 * @param {import("./constants.js").UiLocale} locale
 * @param {Record<string, string | number> | undefined} vars
 */
export function translate(key, locale, vars) {
  const dict = DICTS[locale] || DICTS.en;
  let text = dict[key] ?? DICTS.en[key] ?? key;
  if (vars && typeof text === "string") {
    for (const [k, v] of Object.entries(vars)) {
      text = text.split(`{{${k}}}`).join(String(v));
    }
  }
  return text;
}
