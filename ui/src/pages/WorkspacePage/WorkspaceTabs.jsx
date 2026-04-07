import { normalizeWorkspaceTab, WORKSPACE_TAB_SLUGS } from "./utils/workContext.js";

/** UI labels for workspace tabs; order matches URL `tab` slugs. */
export const WORKSPACE_TAB_CONFIG = [
  { slug: "overview", label: "Overview" },
  { slug: "reader", label: "Reader" },
  { slug: "graph", label: "Graph" },
  { slug: "ask", label: "Ask" },
  { slug: "evidence", label: "Evidence" },
];

/**
 * @param {string} slug
 * @returns {number}
 */
export function workspaceTabIndex(slug) {
  const normalized = normalizeWorkspaceTab(slug);
  const i = WORKSPACE_TAB_SLUGS.indexOf(normalized);
  return i >= 0 ? i : 0;
}

/**
 * @param {number} index
 * @returns {string}
 */
export function workspaceTabSlugFromIndex(index) {
  return WORKSPACE_TAB_SLUGS[index] || "overview";
}
