/**
 * Presentation helpers for Ask citation and source list (no JSX).
 */

import { pickCitationBodyText } from "./citationBodyText.js";
/**
 * @param {Record<string, unknown> | null | undefined} c
 */
export function pickCitationWorkTitle(c) {
  if (!c || typeof c !== "object") return "";
  const raw = c.title ?? c.work_title ?? c.paper_title;
  return raw != null && String(raw).trim() !== "" ? String(raw).trim() : "";
}

/**
 * @param {Record<string, unknown> | null | undefined} c
 * @returns {number | null}
 */
export function citationNumericScore(c) {
  if (!c || typeof c !== "object") return null;
  const raw = c.score ?? c.relevance ?? c.retrieval_score ?? c.similarity;
  if (raw == null || String(raw).trim() === "") return null;
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
}

/**
 * Citation records that only identify works are better presented as source/list
 * items, not evidence passages.
 *
 * @param {Record<string, unknown> | null | undefined} c
 */
export function isWorkOnlyCitation(c) {
  if (!c || typeof c !== "object") return false;
  const wid = c.work_id != null ? String(c.work_id).trim() : "";
  if (!wid) return false;
  const chunkKey = c.chunk_fingerprint ?? c.chunk_id ?? c.fingerprint ?? c.id ?? c.section_path;
  if (chunkKey != null && String(chunkKey).trim() !== "") return false;
  return !pickCitationBodyText(c).trim();
}

/**
 * Prefer paper title; otherwise shorten work_id in simple mode for the headline.
 *
 * @param {Record<string, unknown>} c
 * @param {"simple" | "detailed"} chatDetailLevel
 * @param {{ workOnlyListMode?: boolean }} [options]
 */
export function formatCitationWorkLabel(c, chatDetailLevel, options = {}) {
  const title = pickCitationWorkTitle(c);
  if (title) return title;
  const wid = c.work_id != null ? String(c.work_id).trim() : "";
  if (!wid) return "";
  if (options.workOnlyListMode) {
    return "";
  }
  if (chatDetailLevel === "detailed") return wid;
  return wid.length > 12 ? `${wid.slice(0, 8)}…` : wid;
}

/**
 * Single-line headline: rank, optional numeric score, optional work label.
 *
 * @param {{
 *   rank: string,
 *   citation: Record<string, unknown>,
 *   chatDetailLevel: "simple" | "detailed",
 *   t: (key: string, vars?: Record<string, string>) => string,
 * }} args
 */
export function formatCitationHeadline(args) {
  const { rank, citation, chatDetailLevel, t } = args;
  const workOnly = isWorkOnlyCitation(citation);
  const rankLabel = t(workOnly ? "askPanel.citation.workRankLabel" : "askPanel.citation.rankLabel", { rank });
  const score = citationNumericScore(citation);
  const scorePart = score != null ? ` · ${String(score)}` : "";
  const label = formatCitationWorkLabel(citation, chatDetailLevel, { workOnlyListMode: workOnly });
  const workPart = label ? ` · ${label}` : "";
  return `${rankLabel}${scorePart}${workPart}`;
}
