/**
 * Client-side citation passage hydration for persisted Ask turns (localStorage).
 * Mirrors backend citation_enrichment (quote merge, inventory title → work_id, work_id → title).
 */

import { pickCitationBodyText } from "./citationBodyText.js";

/** @param {unknown} value */
function norm(value) {
  return String(value ?? "").trim();
}

/** @param {unknown} value */
function normalizeTitle(value) {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .split(/\s+/)
    .join(" ");
}

/**
 * @param {Record<string, unknown> | null | undefined} inventory
 * @returns {Map<string, string>} normalized title → work_id
 */
function titleWorkMapFromInventory(inventory) {
  /** @type {Map<string, string>} */
  const m = new Map();
  if (!inventory || typeof inventory !== "object") return m;
  const blocks = [inventory.papers, inventory.paper_matches].filter(Array.isArray);
  for (const block of blocks) {
    for (const raw of block) {
      if (!raw || typeof raw !== "object") continue;
      const wid = norm(raw.work_id);
      const title = normalizeTitle(raw.title ?? raw.work_title ?? raw.paper_title);
      if (wid && title && !m.has(title)) m.set(title, wid);
    }
  }
  return m;
}

/**
 * @param {Record<string, unknown> | null | undefined} inventory
 * @returns {Map<string, string>} work_id → display title (first wins)
 */
function workIdTitleMapFromInventory(inventory) {
  /** @type {Map<string, string>} */
  const m = new Map();
  if (!inventory || typeof inventory !== "object") return m;
  const blocks = [inventory.papers, inventory.paper_matches].filter(Array.isArray);
  for (const block of blocks) {
    for (const raw of block) {
      if (!raw || typeof raw !== "object") continue;
      const wid = norm(raw.work_id);
      const titleRaw = raw.title ?? raw.work_title ?? raw.paper_title;
      const title = titleRaw != null ? String(titleRaw).trim() : "";
      if (wid && title && !m.has(wid)) m.set(wid, title);
    }
  }
  return m;
}

/**
 * @param {Record<string, unknown>[]} citations mutated copies
 * @param {Record<string, unknown> | null | undefined} inventory
 */
function injectTitlesFromInventory(citations, inventory) {
  const wt = workIdTitleMapFromInventory(inventory);
  if (wt.size === 0) return;
  for (const c of citations) {
    const wid = norm(c.work_id);
    if (!wid) continue;
    const hasTitle =
      norm(c.title) || norm(c.work_title) || norm(c.paper_title);
    if (hasTitle) continue;
    const invTitle = wt.get(wid);
    if (invTitle) c.title = invTitle;
  }
}

/**
 * @param {Record<string, unknown>[]} citations mutated copies
 * @param {Record<string, unknown> | null | undefined} inventory
 */
function injectWorkIdsFromInventory(citations, inventory) {
  const tw = titleWorkMapFromInventory(inventory);
  if (tw.size === 0) return;
  for (const c of citations) {
    if (norm(c.work_id)) continue;
    const ct = normalizeTitle(c.title ?? c.work_title ?? c.paper_title);
    if (!ct) continue;
    let wid = tw.get(ct);
    if (!wid && ct.length >= 12) {
      for (const [invTitle, id] of tw.entries()) {
        if (invTitle.length < 12) continue;
        if (ct.includes(invTitle) || invTitle.includes(ct)) {
          wid = id;
          break;
        }
      }
    }
    if (wid) c.work_id = wid;
  }
}

/** @param {Record<string, unknown>} row */
function quoteBody(row) {
  if (!row || typeof row !== "object") return "";
  return norm(row.quote_text || row.text || row.snippet || "");
}

/** @param {Record<string, unknown>} row */
function quoteRowChunkKey(row) {
  if (!row || typeof row !== "object") return "";
  return norm(row.chunk_fingerprint || row.chunk_id || row.fingerprint || row.id);
}

/** @param {Record<string, unknown>} citation */
function citationChunkKey(citation) {
  if (!citation || typeof citation !== "object") return "";
  return norm(citation.chunk_fingerprint || citation.chunk_id || citation.fingerprint || citation.id);
}

function pairKey(workId, chunkKey) {
  return `${workId}\0${chunkKey}`;
}

/**
 * @param {unknown[]} citations
 * @param {unknown[]} quoteCandidates
 * @param {Record<string, unknown> | null | undefined} [inventory]
 * @returns {Record<string, unknown>[]}
 */
export function mergeQuoteCandidatesIntoCitations(citations, quoteCandidates, inventory = null) {
  const cites = Array.isArray(citations) ? citations : [];
  if (cites.length === 0) return [];
  const merged = cites.map((c) => (c && typeof c === "object" ? { ...c } : {}));
  injectWorkIdsFromInventory(merged, inventory);
  injectTitlesFromInventory(merged, inventory);

  const rows = Array.isArray(quoteCandidates) ? quoteCandidates : [];
  if (rows.length === 0) return merged;

  /** @type {Map<string, Record<string, unknown>>} */
  const byPair = new Map();
  /** @type {Map<string, Record<string, unknown>[]>} */
  const byWork = new Map();

  for (const raw of rows) {
    if (!raw || typeof raw !== "object") continue;
    const wid = norm(raw.work_id);
    if (!wid) continue;
    const body = quoteBody(raw);
    if (!body) continue;
    const qk = quoteRowChunkKey(raw);
    if (qk) byPair.set(pairKey(wid, qk), raw);
    const list = byWork.get(wid);
    if (list) list.push(raw);
    else byWork.set(wid, [raw]);
  }

  for (const c of merged) {
    if (pickCitationBodyText(c).trim()) continue;
    const wid = norm(c.work_id);
    if (!wid) continue;
    const fp = citationChunkKey(c);
    const list = byWork.get(wid) || [];
    let picked = null;
    if (fp && byPair.has(pairKey(wid, fp))) {
      picked = byPair.get(pairKey(wid, fp));
    } else if (fp) {
      for (const q of list) {
        if (quoteRowChunkKey(q) === fp) {
          picked = q;
          break;
        }
      }
    } else if (list.length === 1) {
      picked = list[0];
    }
    if (picked) {
      const b = quoteBody(picked);
      if (b) c.excerpt = b;
    }
  }
  return merged;
}
