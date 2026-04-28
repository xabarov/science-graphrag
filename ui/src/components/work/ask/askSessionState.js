import { translate } from "../../i18n/translate.js";
import { readStoredLocale } from "../../i18n/readStoredLocale.js";
import { getRuntimeIntlLocale } from "../../i18n/runtimeIntlLocale.js";
import { getAskHistory } from "./askHistoryState.js";

export const ASK_SESSIONS_STORAGE_KEY = "science-graphrag:askSessions:v1";

export const ASK_SESSIONS_MAX_PER_SCOPE = 8;

export const ASK_SESSION_MAX_TURNS = 24;

function safeStorage() {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

function safeParse(value, fallback) {
  try {
    return JSON.parse(value);
  } catch {
    return fallback;
  }
}

function newSessionId() {
  return `s_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

function newTurnId() {
  try {
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
      return crypto.randomUUID();
    }
  } catch {
    /* ignore */
  }
  return `t_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`;
}

function defaultSessionTitle() {
  try {
    const loc = readStoredLocale();
    return translate("chat.session.defaultTitle", loc);
  } catch {
    return "Chat";
  }
}

/**
 * @param {{ locked: boolean, scopedWorkId?: string | null, workspaceId?: string | null }} ctx
 * @returns {string}
 */
/**
 * Build compact client history for CH4 `history_digest` (oldest → newest, capped).
 * @param {Array<{ query?: string, answer?: string }>} entries
 * @returns {Array<{ user: string, assistant: string }> | null}
 */
export function buildAgentHistoryDigest(entries) {
  if (!Array.isArray(entries) || entries.length === 0) return null;
  const oldestFirst = [...entries].reverse();
  return oldestFirst.slice(-12).map((e) => ({
    user: String(e?.query || "").slice(0, 500),
    assistant: String(e?.answer || "").slice(0, 400),
  }));
}

export function deriveAskScopeKey({ locked, scopedWorkId, workspaceId }) {
  const wid = String(scopedWorkId || "").trim();
  if (locked && wid) {
    return `workspace:${wid}`;
  }
  const ws = String(workspaceId || "").trim();
  if (ws) {
    return `standalone-ws:${ws}`;
  }
  return "standalone";
}

/**
 * When `workspaceId` appears after the user already chatted under `standalone`,
 * copy the local bundle to `standalone-ws:<id>` so the thread does not look empty.
 * No-op if the target scope already has at least one stored turn.
 *
 * @param {string} workspaceId
 */
export function maybeMigrateStandaloneBundleToWorkspaceScope(workspaceId) {
  const storage = safeStorage();
  if (!storage) return;
  const wid = String(workspaceId || "").trim();
  if (!wid) return;
  const fromKey = "standalone";
  const toKey = `standalone-ws:${wid}`;
  if (fromKey === toKey) return;
  const toBundle = getBundle(toKey);
  const toHasTurns = toBundle.sessions.some((s) => (s.entries || []).length > 0);
  if (toHasTurns) return;
  const fromBundle = getBundle(fromKey);
  const fromHasTurns = fromBundle.sessions.some((s) => (s.entries || []).length > 0);
  if (!fromHasTurns) return;
  saveBundle(toKey, {
    activeId: fromBundle.activeId,
    sessions: fromBundle.sessions.map((s) => ({
      ...s,
      entries: [...(s.entries || [])],
    })),
  });
}

/**
 * @param {unknown} item
 * @returns {{ id: string, query: string, workId: string, topK: number, answer: string, citationCount: number, mode: string, savedAt: string, details: Record<string, unknown> | null }}
 */
function normalizeTurn(item) {
  const query = String(item?.query || "").trim();
  const workId = String(item?.workId || "").trim();
  const topK = Number.isFinite(Number(item?.topK)) ? Number(item.topK) : 5;
  const savedAt = item?.savedAt ? String(item.savedAt) : new Date().toISOString();
  const id = String(item?.id || "").trim() || newTurnId();
  const rawDetails = item?.details;
  const details =
    rawDetails && typeof rawDetails === "object" && !Array.isArray(rawDetails) ? { ...rawDetails } : null;
  return {
    id,
    query,
    workId,
    topK,
    answer: String(item?.answer || ""),
    citationCount: Number.isFinite(Number(item?.citationCount)) ? Number(item.citationCount) : 0,
    mode: String(item?.mode || (workId ? "scoped" : "global")),
    savedAt,
    details,
  };
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

function normalizeBundle(raw) {
  if (!raw || typeof raw !== "object") return { activeId: null, sessions: [] };
  const activeId = raw.activeId != null ? String(raw.activeId) : null;
  const sessions = Array.isArray(raw.sessions) ? raw.sessions : [];
  return {
    activeId,
    sessions: sessions
      .map((s) => ({
        id: String(s?.id || "").trim(),
        title: String(s?.title || translate("ask.session.defaultName", readStoredLocale())).trim() || translate("ask.session.defaultName", readStoredLocale()),
        updatedAt: String(s?.updatedAt || ""),
        entries: Array.isArray(s?.entries)
          ? s.entries.map((e) => normalizeTurn(e)).filter((e) => e.id && e.query)
          : [],
      }))
      .filter((s) => s.id),
  };
}

function getBundle(scopeKey) {
  const state = readState();
  const raw = state.scopes[scopeKey];
  return normalizeBundle(raw);
}

function saveBundle(scopeKey, bundle) {
  const state = readState();
  state.scopes[scopeKey] = bundle;
  writeState(state);
}

/**
 * Replace the entire session bundle for a scope (e.g. after server pull).
 *
 * @param {string} scopeKey
 * @param {{ activeId: string | null, sessions: Array<{ id: string, title: string, updatedAt: string, entries: unknown[] }> }} bundle
 */
export function replaceScopeBundle(scopeKey, bundle) {
  const storage = safeStorage();
  if (!storage) return;
  const normalized = normalizeBundle(bundle);
  saveBundle(scopeKey, {
    activeId: normalized.activeId,
    sessions: normalized.sessions,
  });
}

/**
 * One-time import from flat ask history when this scope has no sessions yet.
 *
 * @param {string} scopeKey
 * @param {(item: { workId: string }) => boolean} filterLegacyItem
 */
export function migrateLegacyAskHistoryToSessions(scopeKey, filterLegacyItem) {
  const storage = safeStorage();
  if (!storage) return;
  const bundle = getBundle(scopeKey);
  if (bundle.sessions.length > 0) return;
  const legacy = getAskHistory().filter(filterLegacyItem);
  if (legacy.length === 0) return;
  const id = newSessionId();
  const entries = legacy.slice(0, ASK_SESSION_MAX_TURNS).map((item) => normalizeTurn(item));
  const now = new Date().toISOString();
  saveBundle(scopeKey, {
    activeId: id,
    sessions: [
      {
        id,
        title: translate("ask.session.imported", readStoredLocale()),
        updatedAt: now,
        entries,
      },
    ],
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
  const storage = safeStorage();
  if (!storage) return;
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
  const storage = safeStorage();
  if (!storage) return;
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
  const storage = safeStorage();
  if (!storage) return;
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
  const storage = safeStorage();
  if (!storage) return;
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
  const storage = safeStorage();
  if (!storage) return;
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
  const storage = safeStorage();
  const sid = String(sessionId || "").trim();
  if (!storage || !sid) return { nextActiveId: null, createdFallback: false };
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
  const storage = safeStorage();
  if (!storage) return "";
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
  const storage = safeStorage();
  if (!storage) return;
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
  const storage = safeStorage();
  if (!storage) return;
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
