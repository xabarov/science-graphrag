/**
 * Per-scope/session composer draft (survives Chat -> Settings navigation).
 */
const PREFIX = "science-graphrag:askComposerDraft:v1";

function safeSessionStorage() {
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

function draftKey(scopeKey, sessionId) {
  const sk = String(scopeKey || "default").trim() || "default";
  const sid = String(sessionId || "").trim() || "_none";
  return `${PREFIX}:${sk}:${sid}`;
}

/**
 * @param {string} scopeKey
 * @param {string} sessionId
 * @returns {string}
 */
export function readAskComposerDraft(scopeKey, sessionId) {
  const storage = safeSessionStorage();
  if (!storage) return "";
  try {
    return String(storage.getItem(draftKey(scopeKey, sessionId)) || "");
  } catch {
    return "";
  }
}

/**
 * @param {string} scopeKey
 * @param {string} sessionId
 * @param {string} text
 */
export function writeAskComposerDraft(scopeKey, sessionId, text) {
  const storage = safeSessionStorage();
  if (!storage) return;
  const q = String(text || "");
  const key = draftKey(scopeKey, sessionId);
  try {
    if (!q.trim()) {
      storage.removeItem(key);
      return;
    }
    storage.setItem(key, q);
  } catch {
    /* ignore */
  }
}
