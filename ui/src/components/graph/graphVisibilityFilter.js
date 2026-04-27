/**
 * Client-side visibility over an already-loaded graph (server uses mode=full; types are UI-only).
 */

/** Domain types shown in the Nodes menu (order matters for summaries). */
export const GRAPH_VISIBILITY_DOMAIN_TYPES = /** @type {const} */ ([
  "Work",
  "Author",
  "Method",
  "Dataset",
  "Venue",
  "Institution",
  "Claim",
]);

/**
 * @typedef {{
 *   types: string[],
 *   showExternalWorks: boolean,
 * }} GraphVisibilityValue
 */

/** @returns {GraphVisibilityValue} */
export function defaultGraphVisibility() {
  return {
    types: ["Work", "Author", "Method"],
    showExternalWorks: false,
  };
}

const ALLOWED_TYPES = new Set(GRAPH_VISIBILITY_DOMAIN_TYPES);

/**
 * @param {unknown} raw
 * @returns {GraphVisibilityValue}
 */
export function normalizeGraphVisibilityValue(raw) {
  const def = defaultGraphVisibility();
  if (!raw || typeof raw !== "object") return def;
  const o = /** @type {Record<string, unknown>} */ (raw);
  const typesIn = Array.isArray(o.types) ? o.types.map((x) => String(x || "").trim()).filter((x) => ALLOWED_TYPES.has(x)) : [];
  let types = typesIn.length ? [...new Set(typesIn)] : [...def.types];
  if (types.length === 0) types = [...def.types];
  // Legacy persisted shape: showClaims=false gated claims separately from the Claim checkbox.
  if (o.showClaims === false) {
    types = types.filter((x) => x !== "Claim");
  }
  if (types.length === 0) types = [...def.types];
  return {
    types,
    showExternalWorks: Boolean(o.showExternalWorks),
  };
}

/**
 * @param {unknown} node
 * @returns {boolean}
 */
export function isClaimLikeNode(node) {
  if (!node || typeof node !== "object") return false;
  const n = /** @type {Record<string, unknown>} */ (node);
  const k = String(n.nodeKind || "").trim().toLowerCase();
  const t = String(n.type || "").trim().toLowerCase();
  return k === "claim" || t === "claim";
}

/**
 * External / cited works (workspace graph) — still `Work` type with membership or explicit kind.
 *
 * @param {unknown} node
 * @returns {boolean}
 */
export function isExternalWorkNode(node) {
  if (!node || typeof node !== "object") return false;
  const n = /** @type {Record<string, unknown>} */ (node);
  const k = String(n.nodeKind || "").trim();
  const t = String(n.type || "").trim();
  const mem = String(n.workspaceMembership || "").trim().toLowerCase();
  const workLike = t === "Work" || t === "WorkExternal" || t === "WorkInternal" || k === "Work" || k === "WorkExternal";
  if (!workLike) return false;
  return mem === "external" || k === "WorkExternal" || t === "WorkExternal";
}

/**
 * Map a normalized node to one of GRAPH_VISIBILITY_DOMAIN_TYPES for type-checkbox matching.
 *
 * @param {unknown} node
 * @returns {string}
 */
export function visibilityDomainTypeKey(node) {
  if (!node || typeof node !== "object") return "";
  const n = /** @type {Record<string, unknown>} */ (node);
  if (isClaimLikeNode(n)) return "Claim";
  const k = String(n.nodeKind || "").trim();
  const t = String(n.type || "").trim();
  if (isExternalWorkNode(n)) return "Work";
  if (t === "Work" || t === "WorkInternal" || t === "WorkExternal" || k === "Work") return "Work";
  if (k === "Author" || t === "Author") return "Author";
  if (k === "Method" || t === "Method") return "Method";
  if (k === "Dataset" || t === "Dataset") return "Dataset";
  if (k === "Venue" || t === "Venue") return "Venue";
  if (k === "Institution" || t === "Institution") return "Institution";
  return k || t || "";
}

/**
 * @param {GraphVisibilityValue} v
 * @returns {Set<string>}
 */
function typeSet(v) {
  const raw = Array.isArray(v?.types) ? v.types : [];
  return new Set(raw.map((x) => String(x || "").trim()).filter(Boolean));
}

/**
 * @param {{ nodes?: Array<object>, edges?: Array<object>, meta?: object, workId?: string, warnings?: string[] }} graph
 * @param {GraphVisibilityValue} visibility
 * @returns {{
 *   graph: { nodes: object[], edges: object[], meta: object, workId: string, warnings: string[], nodeCount: number, edgeCount: number },
 *   stats: {
 *     hiddenNodesByType: number,
 *     hiddenNodesAsExternal: number,
 *     hiddenNodesAsClaims: number,
 *       (deprecated; always 0 — claims visibility uses the Claim type checkbox only)
 *     hiddenEdges: number,
 *   },
 * }}
 */
export function applyGraphVisibilityFilter(graph, visibility) {
  const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
  const edges = Array.isArray(graph?.edges) ? graph.edges : [];
  const meta = graph?.meta && typeof graph.meta === "object" ? graph.meta : {};
  const workId = graph?.workId != null ? String(graph.workId) : "";
  const warnings = Array.isArray(graph?.warnings) ? [...graph.warnings] : [];
  const types = typeSet(visibility);

  let hiddenNodesByType = 0;
  let hiddenNodesAsExternal = 0;

  const visibleIds = new Set();
  for (const node of nodes) {
    const id = String(node?.id || "");
    if (!id) continue;

    if (isClaimLikeNode(node)) {
      if (!types.has("Claim")) {
        hiddenNodesByType += 1;
        continue;
      }
      visibleIds.add(id);
      continue;
    }

    if (isExternalWorkNode(node)) {
      if (!visibility.showExternalWorks) {
        hiddenNodesAsExternal += 1;
        continue;
      }
    }

    const dom = visibilityDomainTypeKey(node);
    if (!dom || !types.has(dom)) {
      hiddenNodesByType += 1;
      continue;
    }
    visibleIds.add(id);
  }

  const outEdges = [];
  for (const e of edges) {
    const s = String(e?.source || "");
    const t = String(e?.target || "");
    if (s && t && visibleIds.has(s) && visibleIds.has(t)) outEdges.push(e);
  }
  const hiddenEdges = Math.max(0, edges.length - outEdges.length);
  const outNodes = nodes.filter((n) => visibleIds.has(String(n?.id || "")));

  return {
    graph: {
      ...graph,
      nodes: outNodes,
      edges: outEdges,
      meta,
      workId,
      warnings,
      nodeCount: outNodes.length,
      edgeCount: outEdges.length,
    },
    stats: {
      hiddenNodesByType,
      hiddenNodesAsExternal,
      hiddenNodesAsClaims: 0,
      hiddenEdges,
    },
  };
}
