import { translate } from "../../../../i18n/translate.js";
import { readStoredLocale } from "../../../../i18n/readStoredLocale.js";

export function newSessionId() {
  return `s_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

export function newTurnId() {
  try {
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
      return crypto.randomUUID();
    }
  } catch {
    /* ignore */
  }
  return `t_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`;
}

/**
 * @param {unknown} item
 * @returns {{ id: string, query: string, workId: string, topK: number, answer: string, citationCount: number, mode: string, savedAt: string, details: Record<string, unknown> | null }}
 */
export function normalizeTurn(item) {
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

/**
 * @param {unknown} raw
 * @returns {{ activeId: string | null, sessions: Array<{ id: string, title: string, updatedAt: string, entries: ReturnType<typeof normalizeTurn>[] }> }}
 */
export function normalizeBundle(raw) {
  if (!raw || typeof raw !== "object") return { activeId: null, sessions: [] };
  const activeId = raw.activeId != null ? String(raw.activeId) : null;
  const sessions = Array.isArray(raw.sessions) ? raw.sessions : [];
  const fallbackTitle = translate("ask.session.defaultName", readStoredLocale());
  return {
    activeId,
    sessions: sessions
      .map((s) => ({
        id: String(s?.id || "").trim(),
        title: String(s?.title || fallbackTitle).trim() || fallbackTitle,
        updatedAt: String(s?.updatedAt || ""),
        entries: Array.isArray(s?.entries)
          ? s.entries.map((e) => normalizeTurn(e)).filter((e) => e.id && e.query)
          : [],
      }))
      .filter((s) => s.id),
  };
}
