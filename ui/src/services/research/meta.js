import { apiClient, buildApiUrl, getApiBaseUrl } from "../apiClient.js";

/**
 * Base URL for the research API (no trailing slash). Empty string = same-origin `/v1/*`
 * (Vite dev proxy + FastAPI static deploy).
 */
export function getResearchApiBaseUrl() {
  return getApiBaseUrl();
}

/** GET /health (same origin as API when `VITE_API_BASE_URL` is set). */
export async function getHealth(config) {
  return apiClient.get(buildApiUrl("/health"), config);
}
