/**
 * Pure helpers for {@link WorkspaceGraphToolbar} — flags and stats fragments (no React).
 */

/**
 * @param {string} workspaceId
 * @param {string} contextWorkId
 * @param {boolean} dense
 * @param {boolean} canvasMode
 */
export function computeWorkspaceToolbarFlags(workspaceId, contextWorkId, dense, canvasMode) {
  const wid = String(workspaceId || "").trim();
  const ctxWork = String(contextWorkId || "").trim();
  const filtersEnabled = Boolean(wid);
  const nodesMenuEnabled = filtersEnabled || Boolean(ctxWork);
  /** Single wrapped row: no stacked zone labels; used when canvas or parent dense layout. */
  const useCompactToolbarRow = dense || canvasMode;
  return { wid, ctxWork, filtersEnabled, nodesMenuEnabled, useCompactToolbarRow };
}

/**
 * @param {object | null} stats
 * @param {boolean} filtersEnabled
 * @param {(k: string, opts?: object) => string} t
 * @returns {Array<{ key: string, text: string, tip: string }>}
 */
export function buildWorkspaceToolbarStatsFragments(stats, filtersEnabled, t) {
  if (!stats || typeof stats !== "object" || !filtersEnabled) return [];
  const w = stats.works_count;
  const a = stats.authors_count;
  const x = stats.external_citations;
  const out = [];
  if (typeof w === "number") {
    out.push({
      key: "w",
      text: t("graph.wsToolbar.statsWorks", { count: String(w) }),
      tip: t("graph.wsToolbar.statsWorksTooltip"),
    });
  }
  if (typeof a === "number") {
    out.push({
      key: "a",
      text: t("graph.wsToolbar.statsAuthors", { count: String(a) }),
      tip: t("graph.wsToolbar.statsAuthorsTooltip"),
    });
  }
  if (typeof x === "number") {
    out.push({
      key: "x",
      text: t("graph.wsToolbar.statsExtCites", { count: String(x) }),
      tip: t("graph.wsToolbar.statsExtCitesTooltip"),
    });
  }
  return out;
}
