/**
 * Map raw tool ``error`` codes to the same normalized fallback keys as citation cards
 * (`science_graphrag.agent.evidence_trust.normalize_tool_error_to_fallback_reason`).
 *
 * @param {string} errRaw
 * @returns {string | null}
 */
export function toolTraceErrorToFallbackReason(errRaw) {
  const err = String(errRaw || "").trim().toLowerCase();
  if (!err) return null;
  /** @type {Record<string, string>} */
  const direct = {
    web_search_failed: "source_unreachable",
    arxiv_search_failed: "source_unreachable",
    arxiv_fetch_failed: "source_unreachable",
    unpaywall_request_failed: "source_unreachable",
    unpaywall_invalid_json: "source_unreachable",
    openalex_works_search_failed: "source_unreachable",
    fetch_failed: "source_unreachable",
    host_not_allowed: "host_not_allowed",
    unsupported_scheme: "host_not_allowed",
    private_host_not_allowed: "host_not_allowed",
    redirect_host_not_allowed: "redirect_blocked",
    redirect_unsupported_scheme: "redirect_blocked",
    rate_limited: "rate_limited",
    doi_parse_failed: "metadata_only_fallback",
    invalid_doi: "metadata_only_fallback",
    metadata_only_fallback: "metadata_only_fallback",
    pdf_unavailable: "pdf_unavailable",
    unsupported_pdf_text: "unsupported_pdf_text",
    unknown_tool_failure: "unknown_tool_failure",
  };
  if (direct[err]) return direct[err];
  if (err.includes("rate_limit") || err.endsWith("_429")) return "rate_limited";
  if (err.includes("not_allowed") || err.includes("blocked")) return "host_not_allowed";
  if (err.includes("redirect")) return "redirect_blocked";
  return null;
}

/**
 * @param {(key: string, vars?: Record<string, string>) => string} t
 * @param {string | undefined} errRaw
 * @returns {string}
 */
export function formatToolTraceErrorLine(t, errRaw) {
  const err = String(errRaw || "").trim();
  if (!err) return "";
  const reason = toolTraceErrorToFallbackReason(err);
  if (reason) {
    const key = `askPanel.citation.fallback.${reason}`;
    const localized = t(key);
    if (localized && localized !== key) return localized;
  }
  const errLower = err.toLowerCase();
  const key2 = `askPanel.citation.fallback.${errLower}`;
  const loc2 = t(key2);
  if (loc2 && loc2 !== key2) return loc2;
  return err;
}
