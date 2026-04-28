/**
 * Normalize list/detail payloads from GET /v1/works and GET /v1/works/{id}.
 *
 * @param {Record<string, unknown> | null | undefined} raw
 * @param {string} [fallbackWorkId]
 * @returns {{
 *   work_id: string,
 *   title: string,
 *   year: string | number | null,
 *   doi: string,
 *   arxiv_id: string,
 *   venue: string,
 * }}
 */
export function normalizeWorkListItem(raw, fallbackWorkId = "") {
  const work_id = String(raw?.work_id ?? raw?.id ?? fallbackWorkId ?? "").trim();
  const title = String(raw?.title ?? "").trim();
  const doi = raw?.doi != null ? String(raw.doi).trim() : "";
  const arxiv_id = raw?.arxiv_id != null ? String(raw.arxiv_id).trim() : "";
  const venue = raw?.venue != null ? String(raw.venue).trim() : "";
  const year = raw?.year != null && raw.year !== "" ? raw.year : null;
  return { work_id, title, year, doi, arxiv_id, venue };
}

/**
 * Primary display line: title → doi → arxiv → shortened work_id.
 *
 * @param {Record<string, unknown> | null | undefined} raw
 * @param {string} [fallbackWorkId]
 */
export function formatWorkPrimaryLabel(raw, fallbackWorkId = "") {
  const w = normalizeWorkListItem(raw, fallbackWorkId);
  if (w.title) {
    return w.title.length > 120 ? `${w.title.slice(0, 117)}…` : w.title;
  }
  if (w.doi) return w.doi.length > 80 ? `${w.doi.slice(0, 77)}…` : w.doi;
  if (w.arxiv_id) {
    const ax = w.arxiv_id.includes("/") || w.arxiv_id.startsWith("arxiv") ? w.arxiv_id : `arXiv:${w.arxiv_id}`;
    return ax.length > 48 ? `${ax.slice(0, 45)}…` : ax;
  }
  if (!w.work_id) return "—";
  return w.work_id.length > 22 ? `${w.work_id.slice(0, 18)}…` : w.work_id;
}

/**
 * Secondary line for list rows: year, venue, identifiers.
 *
 * @param {Record<string, unknown> | null | undefined} raw
 * @param {string} [fallbackWorkId]
 */
export function formatWorkSecondaryLine(raw, fallbackWorkId = "") {
  const w = normalizeWorkListItem(raw, fallbackWorkId);
  const primary = formatWorkPrimaryLabel(w, fallbackWorkId);
  const pool = [];
  if (w.year != null && w.year !== "") pool.push(String(w.year));
  if (w.venue) pool.push(w.venue.length > 56 ? `${w.venue.slice(0, 53)}…` : w.venue);
  const ax = w.arxiv_id ? (w.arxiv_id.startsWith("arxiv") ? w.arxiv_id : `arXiv:${w.arxiv_id}`) : "";
  if (w.work_id && primary !== w.work_id) pool.push(w.work_id);
  if (w.doi && primary !== w.doi) pool.push(w.doi);
  if (ax && primary !== ax) pool.push(ax);
  const compact = pool.filter(Boolean);
  const out = compact.slice(0, 4).join(" · ");
  return out.length > 140 ? `${out.slice(0, 137)}…` : out;
}
