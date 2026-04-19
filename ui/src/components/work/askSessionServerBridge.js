/**
 * Map server `/v1/ask-sessions` payloads to local Ask session bundle shape.
 */

/** @param {unknown} id */
export function isServerAskSessionId(id) {
  const s = String(id || "").trim();
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(s);
}

/** @param {Record<string, unknown>} t */
function apiTurnToEntry(t) {
  const query = String(t.query ?? t.q ?? "").trim();
  const workId = String(t.workId ?? t.work_id ?? "").trim();
  const topK = Number.isFinite(Number(t.topK ?? t.top_k)) ? Number(t.topK ?? t.top_k) : 5;
  const savedAt = t.savedAt != null ? String(t.savedAt) : t.saved_at != null ? String(t.saved_at) : new Date().toISOString();
  const id = `${workId || "global"}::${query.toLowerCase()}`;
  return {
    id,
    query,
    workId,
    topK,
    answer: String(t.answer || ""),
    citationCount: Number.isFinite(Number(t.citationCount ?? t.citation_count))
      ? Number(t.citationCount ?? t.citation_count)
      : 0,
    mode: String(t.mode || (workId ? "scoped" : "global")),
    savedAt,
  };
}

/**
 * @param {{ sessions?: unknown[], active_session_id?: string | null }} apiPayload
 * @returns {{ activeId: string | null, sessions: Array<{ id: string, title: string, updatedAt: string, entries: unknown[] }> }}
 */
export function apiSessionsToBundle(apiPayload) {
  const raw = apiPayload?.sessions;
  const sessions = Array.isArray(raw)
    ? raw.map((s) => {
        const row = s && typeof s === "object" ? s : {};
        return {
          id: String(row.id || "").trim(),
          title: String(row.title || "Session").trim() || "Session",
          updatedAt: String(row.updated_at ?? row.updatedAt ?? ""),
          entries: Array.isArray(row.turns) ? row.turns.map(apiTurnToEntry).filter((e) => e.query) : [],
        };
      })
    : [];
  const aid = apiPayload?.active_session_id;
  return {
    activeId: aid != null && String(aid).trim() ? String(aid).trim() : null,
    sessions: sessions.filter((s) => s.id),
  };
}

/**
 * @param {Array<{ query: string, workId: string, topK: number, answer: string, citationCount: number, mode: string, savedAt: string }>} entries
 */
export function entriesToApiTurns(entries) {
  return (entries || []).map((e) => ({
    query: e.query,
    workId: e.workId,
    topK: e.topK,
    answer: e.answer,
    citationCount: e.citationCount,
    mode: e.mode,
    savedAt: e.savedAt,
  }));
}

const SYNC_PREF_KEY = "science-graphrag:askServerSync:v1";

export function readAskServerSyncPref() {
  try {
    if (import.meta.env?.VITE_SYNC_ASK_SESSIONS === "true") return true;
    return window.localStorage.getItem(SYNC_PREF_KEY) === "1";
  } catch {
    return false;
  }
}

/** @param {boolean} on */
export function writeAskServerSyncPref(on) {
  try {
    window.localStorage.setItem(SYNC_PREF_KEY, on ? "1" : "0");
  } catch {
    /* ignore */
  }
}
