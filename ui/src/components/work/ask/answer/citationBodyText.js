/** @param {Record<string, unknown>} c */
export function pickCitationBodyText(c) {
  if (!c || typeof c !== "object") return "";
  const keys = ["excerpt", "snippet", "text", "quote_text", "chunk_text", "passage", "body", "content"];
  for (const k of keys) {
    const v = c[k];
    if (v != null && String(v).trim() !== "") return String(v);
  }
  return "";
}
