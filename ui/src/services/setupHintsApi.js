import { apiClient, buildApiUrl } from "./apiClient.js";

/**
 * Public setup hints (no admin key). Used for lightweight first-run UI.
 * @returns {Promise<{ needs_initial_setup: boolean, llm_api_key_configured: boolean, vl_api_key_configured: boolean }>}
 */
export async function getSetupHints() {
  const res = await apiClient.get(buildApiUrl("/v1/public/setup-hints"));
  return res.data;
}
