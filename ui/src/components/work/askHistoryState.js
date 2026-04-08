export const ASK_HISTORY_STORAGE_KEY = "science-graphrag:askHistory";

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

/**
 * @returns {Array<{id: string, query: string, workId: string, topK: number, answer: string, citationCount: number, mode: string, savedAt: string}>}
 */
export function getAskHistory() {
  const storage = safeStorage();
  if (!storage) return [];
  const raw = storage.getItem(ASK_HISTORY_STORAGE_KEY);
  if (!raw) return [];
  const parsed = safeParse(raw, []);
  if (!Array.isArray(parsed)) return [];
  return parsed
    .map((item) => ({
      id: String(item?.id || "").trim(),
      query: String(item?.query || "").trim(),
      workId: String(item?.workId || "").trim(),
      topK: Number.isFinite(Number(item?.topK)) ? Number(item.topK) : 5,
      answer: String(item?.answer || ""),
      citationCount: Number.isFinite(Number(item?.citationCount)) ? Number(item.citationCount) : 0,
      mode: String(item?.mode || "global"),
      savedAt: String(item?.savedAt || ""),
    }))
    .filter((item) => item.id && item.query);
}

/**
 * @param {{ query: string, workId?: string, topK?: number | string, answer?: string, citationCount?: number, mode?: string, savedAt?: string }} entry
 */
export function rememberAskHistory(entry) {
  const storage = safeStorage();
  if (!storage) return;
  const query = String(entry?.query || "").trim();
  if (!query) return;
  const workId = String(entry?.workId || "").trim();
  const topK = Number.isFinite(Number(entry?.topK)) ? Number(entry.topK) : 5;
  const savedAt = entry?.savedAt ? String(entry.savedAt) : new Date().toISOString();
  const id = `${workId || "global"}::${query.toLowerCase()}`;
  const nextItem = {
    id,
    query,
    workId,
    topK,
    answer: String(entry?.answer || ""),
    citationCount: Number.isFinite(Number(entry?.citationCount)) ? Number(entry.citationCount) : 0,
    mode: String(entry?.mode || (workId ? "scoped" : "global")),
    savedAt,
  };
  const next = [nextItem, ...getAskHistory().filter((item) => item.id !== id)].slice(0, 8);
  storage.setItem(ASK_HISTORY_STORAGE_KEY, JSON.stringify(next));
}

/**
 * @returns {{query: string, workId: string, topK: number, answer: string, citationCount: number, mode: string} | null}
 */
export function getLastAskEntry() {
  return getAskHistory()[0] || null;
}
