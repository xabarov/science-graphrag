/**
 * Normalize API booleans that may arrive as strings (history / loose JSON).
 * @param {unknown} value
 * @returns {boolean}
 */
export function coalesceExternalFlag(value) {
  if (value === true || value === 1) return true;
  if (value === false || value === 0) return false;
  const s = String(value ?? "").trim().toLowerCase();
  return s === "true" || s === "1" || s === "yes";
}

/**
 * Phase 2 trust badges for Ask citation cards (pure helpers).
 * Keys align with backend `science_graphrag.agent.evidence_trust`.
 *
 * @param {Record<string, unknown>} citation
 * @param {"simple" | "detailed"} chatDetailLevel
 * @returns {{ id: string, i18nKey: string }[]}
 */
export function buildCitationTrustBadges(citation, chatDetailLevel) {
  const c = citation && typeof citation === "object" ? citation : {};
  const mode = String(c.evidence_mode || "").trim();
  const provenance = String(c.provenance_kind || "").trim();
  const ext = coalesceExternalFlag(c.is_external);

  /** @type {{ id: string, i18nKey: string }[]} */
  const detailed = [];

  if (ext) {
    detailed.push({ id: "external", i18nKey: "askPanel.citation.trust.external" });
  }
  if (mode === "full_text" || provenance === "workspace_full_text") {
    detailed.push({ id: "fullText", i18nKey: "askPanel.citation.trust.fullText" });
  } else if (mode === "pdf_read" || provenance === "extracted_pdf_text") {
    detailed.push({ id: "pdfRead", i18nKey: "askPanel.citation.trust.pdfRead" });
  } else if (mode === "abstract") {
    detailed.push({ id: "abstract", i18nKey: "askPanel.citation.trust.abstract" });
  } else if (provenance === "openalex_metadata") {
    detailed.push({ id: "openAlexMeta", i18nKey: "askPanel.citation.trust.openAlexMeta" });
  } else if (mode === "metadata_only") {
    detailed.push({ id: "metadataOnly", i18nKey: "askPanel.citation.trust.metadataOnly" });
  } else if (mode === "web_summary") {
    detailed.push({ id: "webSummary", i18nKey: "askPanel.citation.trust.webSummary" });
  } else if (mode === "oa_link") {
    detailed.push({ id: "oaLink", i18nKey: "askPanel.citation.trust.oaLink" });
  }

  const eq = String(c.evidence_quality || "").trim();
  const skipQualityBadge =
    provenance === "openalex_metadata" && eq === "weak";
  if (
    chatDetailLevel === "detailed" &&
    !skipQualityBadge &&
    (eq === "strong" || eq === "medium" || eq === "weak" || eq === "variable")
  ) {
    /** @type {Record<string, string>} */
    const qMap = {
      strong: "askPanel.citation.trust.qualityStrong",
      medium: "askPanel.citation.trust.qualityMedium",
      weak: "askPanel.citation.trust.qualityWeak",
      variable: "askPanel.citation.trust.qualityVariable",
    };
    detailed.push({ id: `quality_${eq}`, i18nKey: qMap[eq] });
  }

  if (chatDetailLevel === "detailed") {
    return detailed;
  }
  /** Simple mode: at most two chips — external (if any) + primary non-external badges. */
  const nonExt = detailed.filter((b) => b.id !== "external");
  const out = [];
  const extBadge = detailed.find((b) => b.id === "external");
  if (extBadge) out.push(extBadge);
  for (const b of nonExt) {
    if (out.length >= 2) break;
    out.push(b);
  }
  return out;
}

/**
 * @param {unknown} reason
 * @returns {string}
 */
export function citationTrustFallbackI18nKey(reason) {
  const r = String(reason || "").trim();
  if (!r) return "";
  return `askPanel.citation.fallback.${r}`;
}

/**
 * @param {(key: string, vars?: Record<string, string>) => string} t
 * @param {Record<string, unknown>} citation
 */
export function formatCitationTrustFallbackText(t, citation) {
  const c = citation && typeof citation === "object" ? citation : {};
  const msg = String(c.fallback_message || "").trim();
  const reason = String(c.fallback_reason || "").trim();
  const key = citationTrustFallbackI18nKey(reason);
  if (key) {
    const localized = t(key);
    if (localized && localized !== key) return localized;
  }
  if (msg) return msg;
  if (reason) return reason.replace(/_/g, " ");
  return "";
}
