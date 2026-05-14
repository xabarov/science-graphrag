import { translate } from "../../../../i18n/translate.js";
import { readStoredLocale } from "../../../../i18n/readStoredLocale.js";
import { getRuntimeIntlLocale } from "../../../../i18n/runtimeIntlLocale.js";
import { newSessionId, normalizeBundle, normalizeTurn } from "./askSessionModel.js";
import { ASK_SESSION_MAX_TURNS, ASK_SESSIONS_MAX_PER_SCOPE } from "./askSessionConstants.js";
import { getBundle, isAskSessionStorageAvailable, saveBundle } from "./askSessionStorage.js";

export { ASK_SESSIONS_STORAGE_KEY } from "./askSessionStorage.js";
export { ASK_SESSIONS_MAX_PER_SCOPE, ASK_SESSION_MAX_TURNS } from "./askSessionConstants.js";
export { buildAgentHistoryDigest } from "./askSessionDigest.js";
export {
  deriveAskScopeKey,
  maybeMigrateStandaloneBundleToWorkspaceScope,
  migrateLegacyAskHistoryToSessions,
} from "./askSessionPolicy.js";

function defaultSessionTitle() {
  try {
    const loc = readStoredLocale();
    return translate("chat.session.defaultTitle", loc);
  } catch {
    return "Chat";
  }
}

/**
 * Replace the entire session bundle for a scope (e.g. after server pull).
 *
 * @param {string} scopeKey
 * @param {{ activeId: string | null, sessions: Array<{ id: string, title: string, updatedAt: string, entries: unknown[] }> }} bundle
 */
export function replaceScopeBundle(scopeKey, bundle) {
  if (!isAskSessionStorageAvailable()) return;
  const normalized = normalizeBundle(bundle);
  saveBundle(scopeKey, {
    activeId: normalized.activeId,
    sessions: normalized.sessions,
  });
}

/**
 * @param {string} scopeKey
 * @param {unknown} [_epoch] Optional; pass a counter so callers re-read after local mutations without memo.
 * @returns {{ activeId: string | null, sessions: Array<{ id: string, title: string, updatedAt: string, entries: unknown[] }> }}
 */
export function readAskSessionUi(scopeKey, _epoch) {
  void _epoch;
  const bundle = getBundle(scopeKey);
  const sorted = [...bundle.sessions].sort((a, b) =>
    (b.updatedAt || "").localeCompare(a.updatedAt || "", getRuntimeIntlLocale()),
  );
  return { activeId: bundle.activeId, sessions: sorted };
}

function ensureActiveSession(scopeKey) {
  let bundle = getBundle(scopeKey);
  if (bundle.sessions.length === 0) {
    const id = newSessionId();
    const now = new Date().toISOString();
    bundle = {
      activeId: id,
      sessions: [
        {
          id,
          title: defaultSessionTitle(),
          updatedAt: now,
          entries: [],
        },
      ],
    };
    saveBundle(scopeKey, bundle);
    return bundle;
  }
  if (!bundle.activeId || !bundle.sessions.some((s) => s.id === bundle.activeId)) {
    const nextActive = bundle.sessions[0].id;
    bundle = { ...bundle, activeId: nextActive };
    saveBundle(scopeKey, bundle);
  }
  return bundle;
}

/**
 * @param {string} scopeKey
 * @param {{ query: string, workId?: string, topK?: number | string, answer?: string, citationCount?: number, mode?: string, savedAt?: string }} entry
 */
export function appendAskSessionTurn(scopeKey, entry) {
  if (!isAskSessionStorageAvailable()) return;
  const bundle = ensureActiveSession(scopeKey);
  const turn = normalizeTurn(entry);
  if (!turn.query) return;
  const sessions = bundle.sessions.map((s) => {
    if (s.id !== bundle.activeId) return s;
    const nextEntries = [turn, ...s.entries.filter((e) => e.id !== turn.id)].slice(0, ASK_SESSION_MAX_TURNS);
    return { ...s, entries: nextEntries, updatedAt: new Date().toISOString() };
  });
  saveBundle(scopeKey, { activeId: bundle.activeId, sessions });
}

/**
 * @param {string} scopeKey
 * @param {string} sessionId
 * @returns {Array<{ id: string, query: string, workId: string, topK: number, answer: string, citationCount: number, mode: string, savedAt: string, details?: Record<string, unknown> | null }>}
 */
export function getAskSessionEntries(scopeKey, sessionId) {
  const bundle = getBundle(scopeKey);
  const sid = String(sessionId || "").trim();
  if (!sid) return [];
  const session = bundle.sessions.find((s) => s.id === sid);
  if (!session || !Array.isArray(session.entries)) return [];
  return [...session.entries];
}

/**
 * Append a turn to a specific session (not necessarily the active one). Used after async agent
 * completes so a mid-flight sidebar switch does not write the answer into the wrong thread.
 *
 * @param {string} scopeKey
 * @param {string} sessionId
 * @param {{ query: string, workId?: string, topK?: number | string, answer?: string, citationCount?: number, mode?: string, savedAt?: string, details?: Record<string, unknown> | null }} entry
 */
export function appendAskSessionTurnToSession(scopeKey, sessionId, entry) {
  if (!isAskSessionStorageAvailable()) return;
  const sid = String(sessionId || "").trim();
  if (!sid) return;
  const bundle = getBundle(scopeKey);
  if (!bundle.sessions.some((s) => s.id === sid)) return;
  const turn = normalizeTurn(entry);
  if (!turn.query) return;
  const sessions = bundle.sessions.map((s) => {
    if (s.id !== sid) return s;
    const nextEntries = [turn, ...s.entries.filter((e) => e.id !== turn.id)].slice(0, ASK_SESSION_MAX_TURNS);
    return { ...s, entries: nextEntries, updatedAt: new Date().toISOString() };
  });
  saveBundle(scopeKey, { activeId: bundle.activeId, sessions });
}

/**
 * Clear all turns for a session (entries newest-first in storage).
 *
 * @param {string} scopeKey
 * @param {string} sessionId
 */
export function clearAskSessionEntries(scopeKey, sessionId) {
  if (!isAskSessionStorageAvailable()) return;
  const sid = String(sessionId || "").trim();
  if (!sid) return;
  const bundle = getBundle(scopeKey);
  if (!bundle.sessions.some((s) => s.id === sid)) return;
  const now = new Date().toISOString();
  const sessions = bundle.sessions.map((s) => (s.id === sid ? { ...s, entries: [], updatedAt: now } : s));
  saveBundle(scopeKey, { activeId: bundle.activeId, sessions });
}

/**
 * Remove the given turn and every turn newer than it (entries are stored newest-first:
 * index 0 = latest). Used for "restart from this user message".
 *
 * @param {string} scopeKey
 * @param {string} sessionId
 * @param {string} turnId
 */
export function truncateAskSessionFromTurn(scopeKey, sessionId, turnId) {
  if (!isAskSessionStorageAvailable()) return;
  const sid = String(sessionId || "").trim();
  const tid = String(turnId || "").trim();
  if (!sid || !tid) return;
  const entries = getAskSessionEntries(scopeKey, sessionId);
  const idx = entries.findIndex((e) => e.id === tid);
  if (idx < 0) return;
  const kept = entries.slice(idx + 1);
  const bundle = getBundle(scopeKey);
  if (!bundle.sessions.some((s) => s.id === sid)) return;
  const now = new Date().toISOString();
  const sessions = bundle.sessions.map((s) => (s.id === sid ? { ...s, entries: kept, updatedAt: now } : s));
  saveBundle(scopeKey, { activeId: bundle.activeId, sessions });
}

/**
 * Remove a single turn from a session (entries are stored newest-first).
 *
 * @param {string} scopeKey
 * @param {string} sessionId
 * @param {string} turnId
 */
export function removeAskSessionTurn(scopeKey, sessionId, turnId) {
  if (!isAskSessionStorageAvailable()) return;
  const sid = String(sessionId || "").trim();
  const tid = String(turnId || "").trim();
  if (!sid || !tid) return;
  const bundle = getBundle(scopeKey);
  if (!bundle.sessions.some((s) => s.id === sid)) return;
  const now = new Date().toISOString();
  const sessions = bundle.sessions.map((s) => {
    if (s.id !== sid) return s;
    const nextEntries = (s.entries || []).filter((e) => String(e?.id || "") !== tid);
    return { ...s, entries: nextEntries, updatedAt: now };
  });
  saveBundle(scopeKey, { activeId: bundle.activeId, sessions });
}

/**
 * Remove a session from the scope bundle. If active session was removed, pick another or create one.
 *
 * @param {string} scopeKey
 * @param {string} sessionId
 * @returns {{ nextActiveId: string | null, createdFallback: boolean }}
 */
export function removeAskSession(scopeKey, sessionId) {
  if (!isAskSessionStorageAvailable()) return { nextActiveId: null, createdFallback: false };
  const sid = String(sessionId || "").trim();
  if (!sid) return { nextActiveId: null, createdFallback: false };
  const bundle = getBundle(scopeKey);
  const filtered = bundle.sessions.filter((s) => s.id !== sid);
  let nextActiveId = bundle.activeId === sid ? null : bundle.activeId;
  let createdFallback = false;
  if (filtered.length === 0) {
    const id = newSessionId();
    const now = new Date().toISOString();
    saveBundle(scopeKey, {
      activeId: id,
      sessions: [{ id, title: defaultSessionTitle(), updatedAt: now, entries: [] }],
    });
    createdFallback = true;
    return { nextActiveId: id, createdFallback };
  }
  if (nextActiveId == null || !filtered.some((s) => s.id === nextActiveId)) {
    nextActiveId = filtered[0].id;
  }
  saveBundle(scopeKey, { activeId: nextActiveId, sessions: filtered });
  return { nextActiveId, createdFallback };
}

/**
 * @param {string} scopeKey
 * @param {string} [title]
 * @returns {string} new session id
 */
export function createAskSession(scopeKey, title) {
  if (!isAskSessionStorageAvailable()) return "";
  const bundle = getBundle(scopeKey);
  const id = newSessionId();
  const now = new Date().toISOString();
  const nextTitle = String(title || "").trim() || defaultSessionTitle();
  const sessions = [{ id, title: nextTitle, updatedAt: now, entries: [] }, ...bundle.sessions].slice(
    0,
    ASK_SESSIONS_MAX_PER_SCOPE,
  );
  saveBundle(scopeKey, { activeId: id, sessions });
  return id;
}

/**
 * @param {string} scopeKey
 * @param {string} sessionId
 */
export function setActiveAskSession(scopeKey, sessionId) {
  if (!isAskSessionStorageAvailable()) return;
  const bundle = getBundle(scopeKey);
  if (!bundle.sessions.some((s) => s.id === sessionId)) return;
  saveBundle(scopeKey, { ...bundle, activeId: sessionId });
}

/**
 * @param {string} scopeKey
 * @param {string} sessionId
 * @param {string} title
 */
export function renameAskSession(scopeKey, sessionId, title) {
  if (!isAskSessionStorageAvailable()) return;
  const bundle = getBundle(scopeKey);
  const next =
    String(title || "").trim().slice(0, 120) || translate("ask.session.defaultName", readStoredLocale());
  const sessions = bundle.sessions.map((s) => (s.id === sessionId ? { ...s, title: next } : s));
  saveBundle(scopeKey, { ...bundle, sessions });
}

/**
 * @param {string} scopeKey
 * @param {string} sessionId
 * @returns {boolean}
 */
export function sessionExistsInScope(scopeKey, sessionId) {
  const sid = String(sessionId || "").trim();
  if (!sid) return false;
  const { sessions } = readAskSessionUi(scopeKey);
  return sessions.some((s) => s.id === sid);
}

/**
 * @param {string} scopeKey
 * @returns {Array<{ id: string, query: string, workId: string, topK: number, answer: string, citationCount: number, mode: string, savedAt: string }>}
 */
export function getActiveSessionEntries(scopeKey) {
  const bundle = ensureActiveSession(scopeKey);
  const active = bundle.sessions.find((s) => s.id === bundle.activeId);
  return active ? active.entries : [];
}
