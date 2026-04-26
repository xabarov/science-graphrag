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
 * True only when admin mode was **explicitly** enabled — either via VITE_ENABLE_ADMIN_SURFACES env
 * or by localStorage key set to "true". Falls back to false (unlike isAdminModeEnabled which
 * defaults to true when nothing is configured). Use for dev-only UI panels (Advanced work_id forms).
 * @returns {boolean}
 */
export function isExplicitAdminMode() {
  let storageValue = null;
  try {
    storageValue = window.localStorage.getItem(ADMIN_MODE_STORAGE_KEY);
  } catch {
    storageValue = null;
  }
  if (storageValue === "true") return true;
  if (storageValue === "false") return false;
  const envValue = import.meta.env.VITE_ENABLE_ADMIN_SURFACES;
  if (typeof envValue === "string") return envValue !== "false";
  return false; // default: hidden unless explicitly configured
}

/**
 * @param {string} pathname
 * @returns {boolean}
 */
export function isAdminPath(pathname) {
  const next = String(pathname || "");
  return next === "/admin" || next.startsWith("/admin/") || Object.hasOwn(LEGACY_ADMIN_ROUTE_MAP, next);
}
