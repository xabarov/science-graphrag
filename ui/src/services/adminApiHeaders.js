/**
 * Optional admin API key for protected routes (`X-Admin-Key`).
 * Source: `localStorage["science-graphrag:adminApiKey:v1"]`.
 * @returns {Record<string, string>}
 */
export function buildAdminApiHeaders() {
  const headers = {};
  let adminKey = "";
  try {
    const ls = window.localStorage.getItem("science-graphrag:adminApiKey:v1");
    if (ls && String(ls).trim()) adminKey = String(ls).trim();
  } catch {
    /* ignore */
  }
  if (adminKey) headers["X-Admin-Key"] = adminKey;

  const token = window.localStorage.getItem("access_token") || window.localStorage.getItem("token");
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}
