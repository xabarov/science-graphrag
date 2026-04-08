/**
 * Canvas draw styles for science-graphrag graph MVP (node types + edge labels).
 */

/** @type {Record<string, { fill: string, stroke: string }>} */
const NODE_TYPE_STYLES = {
  Work: { fill: "rgba(99, 102, 241, 0.22)", stroke: "rgba(129, 140, 248, 0.55)" },
  Method: { fill: "rgba(34, 197, 94, 0.18)", stroke: "rgba(74, 222, 128, 0.48)" },
  Dataset: { fill: "rgba(251, 191, 36, 0.14)", stroke: "rgba(252, 211, 77, 0.5)" },
  Author: { fill: "rgba(168, 85, 247, 0.2)", stroke: "rgba(196, 181, 253, 0.48)" },
  Authorship: { fill: "rgba(148, 163, 184, 0.16)", stroke: "rgba(203, 213, 225, 0.38)" },
  Venue: { fill: "rgba(56, 189, 248, 0.14)", stroke: "rgba(125, 211, 252, 0.48)" },
  Institution: { fill: "rgba(244, 114, 182, 0.12)", stroke: "rgba(251, 207, 232, 0.42)" },
};

const DEFAULT_NODE_STYLE = { fill: "rgba(255,255,255,0.08)", stroke: "rgba(255,255,255,0.2)" };

/**
 * @param {unknown} nodeType
 * @param {{ selected?: boolean, hovered?: boolean }} [opts]
 * @returns {{ fill: string, stroke: string, lineWidth: number }}
 */
/**
 * MUI `sx` fragment for legend Chips so node type colors match the canvas (base, non-selected).
 * @param {unknown} nodeType
 * @returns {object}
 */
export function getScienceGraphLegendNodeChipSx(nodeType) {
  const key = nodeType == null ? "" : String(nodeType).trim();
  const base = NODE_TYPE_STYLES[key] || DEFAULT_NODE_STYLE;
  return {
    height: 22,
    fontSize: "0.75rem",
    backgroundColor: base.fill,
    border: `1px solid ${base.stroke}`,
    color: "rgba(255,255,255,0.82)",
  };
}

export function getScienceGraphNodeStyle(nodeType, opts = {}) {
  const selected = Boolean(opts.selected);
  const hovered = Boolean(opts.hovered);
  const key = nodeType == null ? "" : String(nodeType).trim();
  const base = NODE_TYPE_STYLES[key] || DEFAULT_NODE_STYLE;
  if (selected) {
    return {
      fill: "rgba(99, 102, 241, 0.36)",
      stroke: "rgba(255, 255, 255, 0.88)",
      lineWidth: 2,
    };
  }
  if (hovered) {
    return {
      fill: base.fill,
      stroke: "rgba(255, 255, 255, 0.55)",
      lineWidth: 1.75,
    };
  }
  return { fill: base.fill, stroke: base.stroke, lineWidth: 1 };
}

const EDGE_LABEL_MAX = 18;
const NODE_LABEL_MAX = 28;

/**
 * @param {unknown} raw
 * @param {number} [maxLen]
 * @returns {string}
 */
export function truncateCanvasLabel(raw, maxLen = NODE_LABEL_MAX) {
  const t = raw == null ? "" : String(raw).trim();
  if (!t) return "—";
  if (t.length <= maxLen) return t;
  if (maxLen <= 1) return "…";
  return `${t.slice(0, maxLen - 1)}…`;
}

/**
 * @param {unknown} edgeType
 * @returns {string}
 */
export function edgeTypeCanvasLabel(edgeType) {
  return truncateCanvasLabel(edgeType == null ? "" : String(edgeType).trim(), EDGE_LABEL_MAX);
}
