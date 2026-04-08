export const LEGACY_ADMIN_ROUTE_MAP = {
  "/benchmark": "/admin/benchmarks",
  "/settings": "/admin/settings",
  "/diagnostics": "/admin/diagnostics",
};

/**
 * @param {string} pathname
 * @param {string} [search]
 * @returns {string | null}
 */
export function buildLegacyAdminRedirectTarget(pathname, search = "") {
  const canonicalPath = LEGACY_ADMIN_ROUTE_MAP[pathname];
  if (!canonicalPath) return null;
  return `${canonicalPath}${search || ""}`;
}
