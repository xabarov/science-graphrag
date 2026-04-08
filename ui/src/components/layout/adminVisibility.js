import { LEGACY_ADMIN_ROUTE_MAP } from "../../routeCompatibility.js";

export const ADMIN_MODE_STORAGE_KEY = "science-graphrag:adminMode";

/**
 * Resolve admin mode from local override and env default.
 * Local storage wins when explicitly set to "true" or "false".
 *
 * @param {{ envValue?: string | undefined, storageValue?: string | null | undefined }} input
 * @returns {boolean}
 */
export function resolveAdminModeFlag({ envValue, storageValue }) {
  if (storageValue === "true") return true;
  if (storageValue === "false") return false;
  if (typeof envValue === "string") return envValue !== "false";
  return true;
}

/**
 * @returns {boolean}
 */
export function isAdminModeEnabled() {
  let storageValue = null;
  try {
    storageValue = window.localStorage.getItem(ADMIN_MODE_STORAGE_KEY);
  } catch {
    storageValue = null;
  }
  return resolveAdminModeFlag({
    envValue: import.meta.env.VITE_ENABLE_ADMIN_SURFACES,
    storageValue,
  });
}

/**
 * @param {string} pathname
 * @returns {boolean}
 */
export function isAdminPath(pathname) {
  const next = String(pathname || "");
  return next === "/admin" || next.startsWith("/admin/") || Object.hasOwn(LEGACY_ADMIN_ROUTE_MAP, next);
}
