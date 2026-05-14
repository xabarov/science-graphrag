import { normalizeBundle } from "./askSessionModel.js";

export const ASK_SESSIONS_STORAGE_KEY = "science-graphrag:askSessions:v1";

function safeStorage() {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

/** @returns {boolean} */
export function isAskSessionStorageAvailable() {
  return safeStorage() != null;
}

function safeParse(value, fallback) {
  try {
    return JSON.parse(value);
  } catch {
    return fallback;
  }
}

function readState() {
  const storage = safeStorage();
  if (!storage) return { version: 1, scopes: {} };
  const raw = storage.getItem(ASK_SESSIONS_STORAGE_KEY);
  const parsed = safeParse(raw, null);
  if (!parsed || parsed.version !== 1 || typeof parsed.scopes !== "object" || parsed.scopes === null) {
    return { version: 1, scopes: {} };
  }
  return { version: 1, scopes: { ...parsed.scopes } };
}

function writeState(state) {
  const storage = safeStorage();
  if (!storage) return;
  storage.setItem(ASK_SESSIONS_STORAGE_KEY, JSON.stringify(state));
}

/**
 * @param {string} scopeKey
 */
export function getBundle(scopeKey) {
  const state = readState();
  const raw = state.scopes[scopeKey];
  return normalizeBundle(raw);
}

/**
 * @param {string} scopeKey
 * @param {{ activeId: string | null, sessions: unknown[] }} bundle
 */
export function saveBundle(scopeKey, bundle) {
  const state = readState();
  state.scopes[scopeKey] = bundle;
  writeState(state);
}
