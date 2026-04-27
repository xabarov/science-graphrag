import { APPEARANCE_STORAGE_KEY } from "./appearanceConstants.js";

const VALID = new Set(["dark", "light", "system"]);

/**
 * @param {unknown} raw
 * @returns {"dark"|"light"|"system"}
 */
export function normalizeAppearancePreference(raw) {
  const s = raw == null ? "" : String(raw).trim();
  if (VALID.has(s)) return /** @type {"dark"|"light"|"system"} */ (s);
  return "system";
}

/**
 * @returns {"dark"|"light"|"system"}
 */
export function readAppearancePreference() {
  if (typeof window === "undefined") return "system";
  try {
    return normalizeAppearancePreference(window.localStorage.getItem(APPEARANCE_STORAGE_KEY));
  } catch {
    return "system";
  }
}

/**
 * @param {unknown} pref
 * @returns {"dark"|"light"|"system"}
 */
export function writeAppearancePreference(pref) {
  const normalized = normalizeAppearancePreference(pref);
  if (typeof window === "undefined") return normalized;
  try {
    window.localStorage.setItem(APPEARANCE_STORAGE_KEY, normalized);
  } catch {
    // ignore quota / private mode
  }
  return normalized;
}

/**
 * @returns {boolean}
 */
export function prefersColorSchemeDark() {
  if (typeof window === "undefined") return false;
  try {
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  } catch {
    return false;
  }
}

/**
 * @param {unknown} preference
 * @param {boolean} [prefersDark] defaults to live `prefers-color-scheme: dark`
 * @returns {"dark"|"light"}
 */
export function resolveEffectiveAppearanceMode(preference, prefersDark = prefersColorSchemeDark()) {
  const p = normalizeAppearancePreference(preference);
  if (p === "dark") return "dark";
  if (p === "light") return "light";
  return prefersDark ? "dark" : "light";
}

/**
 * Resolves effective light/dark from a raw localStorage string, matching
 * `index.html` inline boot (roadmap §10.5) and {@link readAppearancePreference} + {@link resolveEffectiveAppearanceMode}.
 *
 * @param {string | null | undefined} rawStored
 * @param {boolean} prefersDarkMatches
 * @returns {"dark"|"light"}
 */
export function resolveEffectiveFromStoredRaw(rawStored, prefersDarkMatches) {
  return resolveEffectiveAppearanceMode(normalizeAppearancePreference(rawStored), prefersDarkMatches);
}

/**
 * @param {"dark"|"light"} effective
 */
export function applyDocumentColorScheme(effective) {
  const e = effective === "light" ? "light" : "dark";
  if (typeof document === "undefined") return;
  document.documentElement.dataset.colorScheme = e;
  document.documentElement.style.colorScheme = e;
}
