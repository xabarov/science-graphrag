/**
 * Workspace graph helpers: author-related aggregator detection and expand URL collection.
 *
 * **Reader / authorship parity:** Collapse of duplicate authorship semantics for the reader view
 * (`collapse_authorship_for_reader_view` in `science_graphrag/api/graph_reader_projection/authorship_collapse.py`,
 * tests in `tests/api/test_collapse_authorship_reader_view.py`) is applied on the server when building
 * workspace and work+workspace graph payloads. The `useGraphWorkspaceData` hook consumes normalized API
 * output only; {@link projectAuthorSemanticGraph} stays an identity pass-through so the client does not
 * mirror membership semantics that would drift from the backend contract.
 */

/** Aggregator kinds that represent author/authorship neighborhoods on a Work. */
export const AUTHOR_AGGREGATOR_KINDS = new Set([
  "author_of_work",
  "authorship_of_work",
  "authorshipreification_of_work",
]);

/**
 * @param {unknown} node normalized graph node from {@link normalizeGraphPayload}
 * @returns {boolean}
 */
export function isAuthorAggregatorNode(node) {
  if (!node || typeof node !== "object") return false;
  const n = /** @type {Record<string, unknown>} */ (node);
  if (String(n.nodeKind || "") !== "Aggregator") return false;
  const raw = n.raw && typeof n.raw === "object" ? /** @type {Record<string, unknown>} */ (n.raw) : {};
  const hintsRaw = raw.aggregation_hints ?? raw.aggregationHints;
  const hints = hintsRaw && typeof hintsRaw === "object" && !Array.isArray(hintsRaw) ? hintsRaw : {};
  const kind = String((hints.aggregator_kind ?? hints.aggregatorKind) || "")
    .trim()
    .toLowerCase();
  return AUTHOR_AGGREGATOR_KINDS.has(kind);
}

/**
 * @param {unknown} node normalized graph node
 * @returns {boolean}
 */
export function isAuthorshipLikeNode(node) {
  if (!node || typeof node !== "object") return false;
  const n = /** @type {Record<string, unknown>} */ (node);
  const t = String(n.type || "").trim();
  const k = String(n.nodeKind || "").trim();
  return t === "Authorship" || k === "Authorship" || k === "AuthorshipReification";
}

/**
 * @param {unknown} hints aggregation_hints object
 * @returns {string}
 */
function readExpandEndpoint(hints) {
  if (!hints || typeof hints !== "object" || Array.isArray(hints)) return "";
  const h = /** @type {Record<string, unknown>} */ (hints);
  return String(h.expand_endpoint ?? h.expandEndpoint ?? "").trim();
}

/**
 * Unique expand_endpoint values for author-related aggregators (for hidden prefetch).
 *
 * @param {{ nodes?: Array<object> }} graph normalized graph
 * @returns {string[]}
 */
export function collectAuthorAggregatorExpandEndpoints(graph) {
  const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
  const out = [];
  const seen = new Set();
  for (const n of nodes) {
    if (!isAuthorAggregatorNode(n)) continue;
    const raw = n.raw && typeof n.raw === "object" ? /** @type {Record<string, unknown>} */ (n.raw) : {};
    const hintsRaw = raw.aggregation_hints ?? raw.aggregationHints;
    const ep = readExpandEndpoint(
      hintsRaw && typeof hintsRaw === "object" && !Array.isArray(hintsRaw) ? hintsRaw : {},
    );
    if (!ep || seen.has(ep)) continue;
    seen.add(ep);
    out.push(ep);
  }
  return out;
}

/**
 * Pass-through: server emits reader-safe authorship (AUTHORED, no Authorship) for workspace.
 *
 * @param {{
 *   nodes: Array<object>,
 *   edges: Array<object>,
 *   workId?: string,
 *   meta?: object,
 *   warnings?: string[],
 *   nodeCount?: number,
 *   edgeCount?: number,
 *   selectedNodeId?: string,
 * }} graph normalized graph from {@link normalizeGraphPayload}
 * @returns {typeof graph}
 */
export function projectAuthorSemanticGraph(graph) {
  return graph;
}
