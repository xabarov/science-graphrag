import { buildAdminApiHeaders } from "../../services/adminApiHeaders.js";
import { apiClient, buildApiUrl } from "../../services/apiClient.js";

function authHeaders() {
  return buildAdminApiHeaders();
}

export async function getSettingsSchema() {
  const res = await apiClient.get(buildApiUrl("/v1/settings/schema"), { headers: authHeaders() });
  return res.data;
}

export async function getSettingsSnapshot() {
  const res = await apiClient.get(buildApiUrl("/v1/settings"), { headers: authHeaders() });
  return res.data;
}

export async function updateLlmSettings(payload) {
  const res = await apiClient.patch(buildApiUrl("/v1/settings/llm"), payload, { headers: authHeaders() });
  return res.data;
}

export async function updateIngestionSettings(payload) {
  const res = await apiClient.patch(buildApiUrl("/v1/settings/ingestion"), payload, {
    headers: authHeaders(),
  });
  return res.data;
}

export async function updateGeneralSettings(payload) {
  const res = await apiClient.patch(buildApiUrl("/v1/settings/general"), payload, {
    headers: authHeaders(),
  });
  return res.data;
}

export async function updateStorageSettings(payload) {
  const res = await apiClient.patch(buildApiUrl("/v1/settings/storage"), payload, {
    headers: authHeaders(),
  });
  return res.data;
}

export async function updateBenchmarkSettings(payload) {
  const res = await apiClient.patch(buildApiUrl("/v1/settings/benchmark"), payload, {
    headers: authHeaders(),
  });
  return res.data;
}

export async function updateAgentToolsSettings(payload) {
  const res = await apiClient.patch(buildApiUrl("/v1/settings/agent_tools"), payload, {
    headers: authHeaders(),
  });
  return res.data;
}

export async function testAgentToolsSource(sourceId) {
  const res = await apiClient.post(
    buildApiUrl("/v1/settings/agent_tools/test_source"),
    { source_id: sourceId },
    { headers: authHeaders() },
  );
  return res.data;
}

/**
 * Explicit operator reveal of a managed vault secret (audit logged server-side).
 *
 * @param {"extraction"|"chat"|"vision"|"embeddings"} task
 * @returns {Promise<string>}
 */
export async function revealLlmTaskSecret(task) {
  const res = await apiClient.post(
    buildApiUrl("/v1/settings/llm/reveal-secret"),
    { task },
    { headers: authHeaders() },
  );
  const secret = res.data?.secret;
  return typeof secret === "string" ? secret : "";
}

export async function testLlmConnection(payload) {
  const res = await apiClient.post(buildApiUrl("/v1/settings/llm/test"), payload, {
    headers: authHeaders(),
  });
  return res.data;
}

export async function testLlmTaskConnection({ task, use_saved_secret = true }) {
  return testLlmConnection({ task, use_saved_secret });
}
