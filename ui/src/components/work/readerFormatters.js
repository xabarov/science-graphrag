/** Max chars for combined extracted markdown in Reader body (performance). */
export const READER_COMBINED_MARKDOWN_MAX_CHARS = 120_000;

/** Max chars per chunk preview in advanced chunk list. */
export const READER_CHUNK_PREVIEW_MAX_CHARS = 4000;

/** Max chars per evidence quote line in Reader claims section. */
export const READER_CLAIM_EVIDENCE_QUOTE_MAX = 600;

/**
 * @param {unknown} items
 * @returns {Array<Record<string, unknown>>}
 */
export function sortChunksByOrder(items) {
  if (!Array.isArray(items)) return [];
  return [...items].sort((a, b) => (Number(a?.order) || 0) - (Number(b?.order) || 0));
}

/**
 * Build one plain-text/markdown-ish document from chunk rows (sorted by order).
 * @param {unknown} items
 * @returns {string}
 */
export function buildCombinedMarkdownFromChunks(items) {
  const sorted = sortChunksByOrder(items);
  if (!sorted.length) return "";
  return sorted
    .map((ch) => {
      const head = ch?.section_path ? `## ${ch.section_path}\n\n` : "";
      return `${head}${ch?.text || ""}`.trim();
    })
    .filter(Boolean)
    .join("\n\n---\n\n");
}

/**
 * Truncate for display with a single ellipsis suffix when truncated.
 * @param {unknown} text
 * @param {number} maxLen — must be > 0 to truncate; if <= 0, returns full string (no truncation).
 * @returns {{ text: string, truncated: boolean }}
 */
export function truncateWithEllipsis(text, maxLen) {
  if (text == null || typeof text !== "string") {
    return { text: "", truncated: false };
  }
  if (maxLen <= 0) {
    return { text, truncated: false };
  }
  if (text.length <= maxLen) {
    return { text, truncated: false };
  }
  return { text: `${text.slice(0, maxLen)}…`, truncated: true };
}

/**
 * Whether a chunk row matches trace focus (fingerprint and/or section).
 * @param {Record<string, unknown>} chunk
 * @param {{ focusedFingerprint?: string, focusedSection?: string }} focus
 */
export function isChunkFocused(chunk, { focusedFingerprint = "", focusedSection = "" } = {}) {
  const fingerprint = String(chunk?.chunk_fingerprint || "");
  const sectionPath = String(chunk?.section_path || "");
  const fpMatch = Boolean(focusedFingerprint && fingerprint === focusedFingerprint);
  const secMatch = Boolean(focusedSection && sectionPath === focusedSection);
  return fpMatch || secMatch;
}
