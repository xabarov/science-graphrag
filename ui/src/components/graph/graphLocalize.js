/**
 * Graph display strings keyed by raw Neo4j relationship types and node_kind values (Wave GR7).
 *
 * @typedef {(key: string, vars?: Record<string, string | number>) => string} GraphTranslateFn
 */

/**
 * @param {unknown} edge
 * @returns {string}
 */
function rawEdgeType(edge) {
  const e = edge && typeof edge === "object" ? /** @type {Record<string, unknown>} */ (edge) : {};
  const typ = e.type == null ? "" : String(e.type).trim();
  return typ.toUpperCase();
}

/**
 * Human-readable edge label from **raw** `edge.type` only (ignores `displayType` so locale controls copy).
 *
 * @param {unknown} edge
 * @param {GraphTranslateFn} t
 * @returns {string}
 */
export function localizeEdgeType(edge, t) {
  const typ = rawEdgeType(edge);
  if (!typ) {
    const out = t("graph.edgeType.EDGE");
    return out === "graph.edgeType.EDGE" ? "edge" : out;
  }
  const key = `graph.edgeType.${typ}`;
  const out = t(key);
  if (out !== key) return out;
  const human = typ.replace(/_/g, " ").toLowerCase();
  const fb = t("graph.edgeType._other", { type: human });
  if (fb !== "graph.edgeType._other") return fb;
  return human;
}

/** @type {Map<string, string>} */
const NODE_KIND_CANON = new Map(
  Object.entries({
    work: "Work",
    workinternal: "WorkInternal",
    workexternal: "WorkExternal",
    author: "Author",
    method: "Method",
    dataset: "Dataset",
    venue: "Venue",
    institution: "Institution",
    aggregator: "Aggregator",
    authorshipreification: "AuthorshipReification",
    authorship: "Authorship",
    claim: "Claim",
    node: "Node",
  }),
);

/**
 * @param {string} kind
 * @returns {string}
 */
function canonNodeKind(kind) {
  const s = String(kind || "").trim();
  if (!s) return "Node";
  const hit = NODE_KIND_CANON.get(s.toLowerCase());
  return hit || s;
}

function rawNodeKind(node) {
  const n = node && typeof node === "object" ? /** @type {Record<string, unknown>} */ (node) : {};
  const k = n.nodeKind != null && String(n.nodeKind).trim() ? String(n.nodeKind) : n.type != null && String(n.type).trim() ? String(n.type) : "Node";
  return canonNodeKind(k);
}

/**
 * Localized node kind / Neo4j-oriented label for chips and the detail panel.
 *
 * @param {unknown} node
 * @param {GraphTranslateFn} t
 * @returns {string}
 */
export function localizeNodeKind(node, t) {
  const kind = rawNodeKind(node);
  const nk = `graph.nodeKind.${kind}`;
  let out = t(nk);
  if (out !== nk) return out;
  const wk = `graph.wsToolbar.nodeType.${kind}`;
  out = t(wk);
  if (out !== wk) return out;
  return kind;
}

/**
 * @param {unknown} node
 * @returns {Record<string, unknown> | null}
 */
function readAggregationHints(node) {
  const n = node && typeof node === "object" ? /** @type {Record<string, unknown>} */ (node) : {};
  const raw = n.raw && typeof n.raw === "object" ? /** @type {Record<string, unknown>} */ (n.raw) : {};
  const h = raw.aggregation_hints ?? raw.aggregationHints;
  if (h && typeof h === "object" && !Array.isArray(h)) return /** @type {Record<string, unknown>} */ (h);
  return null;
}

/**
 * Localized one-line title for an Aggregator node (replaces EN-only `display_label` like "8 author").
 *
 * @param {unknown} node
 * @param {GraphTranslateFn} t
 * @returns {string}
 */
export function localizeAggregatorTitle(node, t) {
  const hints = readAggregationHints(node);
  const countRaw = hints?.count;
  const count = typeof countRaw === "number" && Number.isFinite(countRaw) ? countRaw : Number(countRaw);
  const n = Number.isFinite(count) ? count : 0;
  const aggKind = hints?.aggregator_kind != null ? String(hints.aggregator_kind).trim().toLowerCase() : "";
  if (aggKind) {
    const key = `graph.aggregator.kind.${aggKind}`;
    let out = t(key, { count: n });
    if (out !== key) return out;
  }
  const n2 = node && typeof node === "object" ? /** @type {Record<string, unknown>} */ (node) : {};
  const fbLabel = n2.displayLabel != null && String(n2.displayLabel).trim() ? String(n2.displayLabel) : n2.label != null && String(n2.label).trim() ? String(n2.label) : "";
  if (fbLabel) return fbLabel;
  const fbKey = "graph.aggregator.kind._other";
  const humanKind = aggKind ? aggKind.replace(/_/g, " ") : "group";
  let out = t(fbKey, { count: n, kind: humanKind });
  if (out !== fbKey) return out;
  return `${n} ${humanKind}`;
}

/**
 * Localized subtitle under aggregator title (replaces fixed EN "Click to expand").
 *
 * @param {GraphTranslateFn} t
 * @returns {string}
 */
export function localizeAggregatorSubtitle(t) {
  return t("graph.aggregator.subtitleExpand");
}

/**
 * Edge type key for legend chips (raw Neo4j type, uppercased).
 *
 * @param {string} edgeType
 * @param {GraphTranslateFn} t
 * @returns {string}
 */
export function localizeEdgeTypeKey(edgeType, t) {
  const fake = { type: edgeType };
  return localizeEdgeType(fake, t);
}

/**
 * Localized property key for graph node "Key properties" (snake_case API keys).
 *
 * @param {unknown} rawKey
 * @param {GraphTranslateFn} t
 * @returns {string}
 */
/**
 * Labels for Claim node `properties` (graph payload). Extend `graph.claimProperty.*` in i18n when adding Neo4j fields.
 *
 * @param {string} rawKey
 * @param {GraphTranslateFn} t
 * @returns {string}
 */
export function localizeClaimPropertyKey(rawKey, t) {
  const k = String(rawKey || "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "_");
  if (!k) return String(rawKey || "");
  const i18nKey = `graph.claimProperty.${k}`;
  let out = t(i18nKey);
  if (out !== i18nKey) return out;
  return localizeWorkPropertyKey(rawKey, t);
}

export function localizeWorkPropertyKey(rawKey, t) {
  const k = String(rawKey || "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "_");
  if (!k) return String(rawKey || "");
  const i18nKey = `graph.workProperty.${k}`;
  const out = t(i18nKey);
  if (out !== i18nKey) return out;
  return String(rawKey)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * Optional longer explanation for edge direction hint (e.g. "lateral" in neighborhood lists).
 *
 * @param {string} hint
 * @param {GraphTranslateFn} t
 * @returns {string} empty when no dedicated hint
 */
export function localizeDirectionHintTooltip(hint, t) {
  const h = String(hint || "").trim().toLowerCase();
  if (!h) return "";
  const key = `graph.detailPanel.direction.${h}Hint`;
  const out = t(key);
  return out !== key ? out : "";
}
