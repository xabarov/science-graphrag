/**
 * User-facing error strings for agent / Ask UI (no transport).
 * @param {(key: string) => string} t
 * @param {unknown} msg
 */
export function formatAskAgentUiError(t, msg) {
  const s = String(msg || "").trim();
  if (!s) return t("askPanel.agentIncompleteTurn");
  if (/\(code 403\)/.test(s) || (/403/.test(s) && /Upstream LLM/i.test(s))) return t("chat.errors.llmForbidden");
  if (/\(code 401\)/.test(s) || (/401/.test(s) && /Upstream LLM/i.test(s))) return t("chat.errors.llmUnauthorized");
  return s;
}
