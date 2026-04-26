import { apiClient, buildApiUrl } from "../apiClient.js";

/** GET/PATCH/DELETE /v1/ask-sessions — server-backed Ask history (optional UI integration). */
export async function listAskSessions(scope) {
  const s = encodeURIComponent(String(scope ?? "").trim());
  return apiClient.get(buildApiUrl(`/v1/ask-sessions?scope=${s}`));
}

export async function createAskSession(scope, { title } = {}) {
  return apiClient.post(buildApiUrl("/v1/ask-sessions"), { scope, title });
}

export async function patchAskSession(scope, sessionId, body) {
  const sid = encodeURIComponent(String(sessionId ?? "").trim());
  const s = encodeURIComponent(String(scope ?? "").trim());
  return apiClient.patch(buildApiUrl(`/v1/ask-sessions/${sid}?scope=${s}`), body);
}

export async function deleteAskSession(scope, sessionId) {
  const sid = encodeURIComponent(String(sessionId ?? "").trim());
  const s = encodeURIComponent(String(scope ?? "").trim());
  return apiClient.delete(buildApiUrl(`/v1/ask-sessions/${sid}?scope=${s}`));
}
