/**
 * View-model helpers for benchmark case inspector (Phase 4).
 * Server sends ``highlights`` / ``evidence_links`` on run case detail; this module
 * fills gaps for fixture-only mode and older API responses.
 */

/**
 * @param {Record<string, unknown> | null | undefined} artifacts
 * @returns {Array<{ id: string, label: string, path_relative_to_repo?: string, run_id?: string }>}
 */
export function buildEvidenceLinksFromArtifacts(artifacts) {
  if (!artifacts || typeof artifacts !== "object") return [];
  /** @type {Array<{ id: string, label: string, path_relative_to_repo?: string, run_id?: string }>} */
  const links = [];
  if (artifacts.fixture_dir_relative) {
    links.push({
      id: "fixture_dir",
      label: "fixture_directory",
      path_relative_to_repo: String(artifacts.fixture_dir_relative),
    });
  }
  const art = artifacts.article;
  if (art && typeof art === "object" && art.path_relative_to_repo) {
    links.push({
      id: "article",
      label: "article_md",
      path_relative_to_repo: String(art.path_relative_to_repo),
    });
  }
  const variants = artifacts.gold_variants;
  if (Array.isArray(variants)) {
    variants.forEach((gv) => {
      if (gv?.present && gv.path_relative_to_repo) {
        links.push({
          id: `gold_${gv.id || "variant"}`,
          label: String(gv.id || "gold"),
          path_relative_to_repo: String(gv.path_relative_to_repo),
        });
      }
    });
  }
  const sg = artifacts.semantic_gold;
  if (sg && typeof sg === "object" && sg.path_relative_to_repo) {
    links.push({
      id: "semantic_gold",
      label: "semantic_gold",
      path_relative_to_repo: String(sg.path_relative_to_repo),
    });
  }
  const lrh = artifacts.last_run_hints;
  if (lrh && typeof lrh === "object" && lrh.run_id) {
    links.push({
      id: "last_completed_run",
      label: "last_completed_run",
      run_id: String(lrh.run_id),
    });
  }
  return links;
}

/**
 * Minimal client-side highlights when API did not attach ``highlights`` (fixture-only).
 * @param {string} family
 * @returns {{ headline: string, failed_checks: string[], issues: unknown[], family: string }}
 */
export function buildFixtureCatalogHighlights(family) {
  return {
    headline: "",
    failed_checks: [],
    issues: [],
    family: family || "layer1",
  };
}

/**
 * @param {Record<string, unknown> | null | undefined} caseDetail
 * @returns {Record<string, unknown>}
 */
export function getHighlightsOrFallback(caseDetail) {
  const h = caseDetail?.highlights;
  if (h && typeof h === "object") return /** @type {Record<string, unknown>} */ (h);
  const fam = (caseDetail?.family && String(caseDetail.family)) || "layer1";
  return buildFixtureCatalogHighlights(fam);
}
