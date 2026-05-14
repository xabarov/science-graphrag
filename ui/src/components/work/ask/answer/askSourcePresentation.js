/**
 * Pure helpers for Ask source / citation list presentation (no JSX).
 */

import { pickCitationBodyText } from "./citationBodyText.js";
import { isWorkOnlyCitation } from "./citationDisplay.js";

/**
 * @param {Record<string, unknown> | null | undefined} normalized
 */
export function deriveAnswerClass(normalized) {
  return normalized?.answer_class != null ? String(normalized.answer_class).trim() : "";
}

/**
 * @param {string} answerClass
 * @param {Record<string, unknown>[]} citations
 */
export function deriveShowAsFoundPapers(answerClass, citations) {
  const allWorkOnly = citations.length > 0 && citations.every((c) => isWorkOnlyCitation(c));
  return answerClass === "inventory" || allWorkOnly;
}

/**
 * @param {string} answerClass
 * @param {Record<string, unknown>[]} citations
 */
export function deriveSourceListPresentation(answerClass, citations) {
  const allWebOnly =
    citations.length > 0 &&
    citations.every((c) => String(c?.source_type || "").toLowerCase() === "web");
  const showAsFoundPapers = deriveShowAsFoundPapers(answerClass, citations);
  const citationListLabelKey = allWebOnly
    ? "askPanel.citations.webTitle"
    : showAsFoundPapers
      ? "askPanel.citations.inventoryTitle"
      : "askPanel.citations.title";
  const missingPassageCount = citations.filter((c) => !pickCitationBodyText(c).trim()).length;
  const suppressMissingPassageChrome = showAsFoundPapers || allWebOnly;
  const allPassagesMissing =
    !suppressMissingPassageChrome && citations.length > 0 && missingPassageCount === citations.length;
  const somePassagesMissing =
    !suppressMissingPassageChrome && missingPassageCount > 0 && missingPassageCount < citations.length;
  return {
    showAsFoundPapers,
    citationListLabelKey,
    allPassagesMissing,
    somePassagesMissing,
    suppressMissingPassageChrome,
  };
}

/**
 * @param {Record<string, unknown>} c
 * @param {number} index
 */
export function citationRankFromRow(c, index) {
  if (c.rank != null && String(c.rank).trim() !== "") return String(c.rank);
  if (c.citation_index != null && String(c.citation_index).trim() !== "") return String(c.citation_index);
  return String(index + 1);
}

/**
 * @param {string} workspaceId
 * @param {string} chunkFingerprint
 * @param {string} sectionPath
 * @param {string} citationIndex
 */
export function citationTraceExtras(workspaceId, chunkFingerprint, sectionPath, citationIndex) {
  const base = { chunkFingerprint, section: sectionPath, citation: citationIndex };
  const ws = String(workspaceId || "").trim();
  return ws ? { ...base, workspaceId: ws } : base;
}
