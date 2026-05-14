export function pickQuoteWorkTitle(c) {
  if (!c || typeof c !== "object") return "";
  const raw = c.title ?? c.work_title ?? c.paper_title;
  return raw != null ? String(raw).trim() : "";
}
