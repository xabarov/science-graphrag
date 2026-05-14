/**
 * Client-side history shaping for agent CH4 `history_digest` (oldest → newest, capped).
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
