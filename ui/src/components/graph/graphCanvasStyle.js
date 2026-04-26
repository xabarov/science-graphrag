/**
 * Canvas draw styles for science-graphrag graph MVP (node types + edge labels).
 */

import AccountBalanceOutlinedIcon from "@mui/icons-material/AccountBalanceOutlined";
import ArticleOutlinedIcon from "@mui/icons-material/ArticleOutlined";
import LinkOutlinedIcon from "@mui/icons-material/LinkOutlined";
import MenuBookOutlinedIcon from "@mui/icons-material/MenuBookOutlined";
import OpenInNewOutlinedIcon from "@mui/icons-material/OpenInNewOutlined";
import PersonOutlinedIcon from "@mui/icons-material/PersonOutlined";
import PsychologyOutlinedIcon from "@mui/icons-material/PsychologyOutlined";
import StorageOutlinedIcon from "@mui/icons-material/StorageOutlined";

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
 * MUI icon component per graph node kind / type (toolbar, legend, chips).
 * @type {Record<string, import("react").ComponentType<{ sx?: object }>>}
 */
export const NODE_TYPE_ICON_MAP = {
  Work: ArticleOutlinedIcon,
  WorkInternal: ArticleOutlinedIcon,
  WorkExternal: OpenInNewOutlinedIcon,
  Author: PersonOutlinedIcon,
  Authorship: LinkOutlinedIcon,
  AuthorshipReification: LinkOutlinedIcon,
  Method: PsychologyOutlinedIcon,
  Dataset: StorageOutlinedIcon,
  Venue: MenuBookOutlinedIcon,
  Institution: AccountBalanceOutlinedIcon,
};

/**
 * @param {unknown} nodeType
 * @returns {import("react").ComponentType<{ sx?: object }> | null}
 */
export function getScienceGraphNodeTypeIcon(nodeType) {
  const key = nodeType == null ? "" : String(nodeType).trim();
  return NODE_TYPE_ICON_MAP[key] || null;
}

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

/**
 * @param {unknown} nodeType
 * @param {{ selected?: boolean, hovered?: boolean, workspaceMembership?: string, nodeKind?: string }} [opts]
 * @returns {{ fill: string, stroke: string, lineWidth: number, strokeDash?: number[] }}
 */
export function getScienceGraphNodeStyle(nodeType, opts = {}) {
  if (String(opts.nodeKind || "") === "Aggregator") {
    return {
      fill: "rgba(99, 102, 241, 0.12)",
      stroke: "rgba(99, 102, 241, 0.6)",
      lineWidth: 1.5,
      strokeDash: [6, 3],
    };
  }
  const selected = Boolean(opts.selected);
  const hovered = Boolean(opts.hovered);
  const key = nodeType == null ? "" : String(nodeType).trim();
  const base = NODE_TYPE_STYLES[key] || DEFAULT_NODE_STYLE;
  const ext = String(opts.workspaceMembership || "").toLowerCase() === "external";
  const dim = (rgba) => {
    const m = String(rgba).match(/rgba?\(([^)]+)\)/);
    if (!m) return rgba;
    const parts = m[1].split(",").map((s) => s.trim());
    if (parts.length === 4) {
      const a = Math.min(0.22, parseFloat(parts[3]) * 0.35 || 0.08);
      return `rgba(${parts[0]}, ${parts[1]}, ${parts[2]}, ${a})`;
    }
    return rgba;
  };
  const fillBase = ext ? dim(base.fill) : base.fill;
  const strokeBase = ext ? dim(base.stroke) : base.stroke;
  const lwBase = ext ? 1 : opts.workspaceMembership === "internal" ? 1.5 : 1;
  if (selected) {
    return {
      fill: "rgba(99, 102, 241, 0.36)",
      stroke: "rgba(255, 255, 255, 0.88)",
      lineWidth: 2,
    };
  }
  if (hovered) {
    return {
      fill: fillBase,
      stroke: "rgba(255, 255, 255, 0.55)",
      lineWidth: 1.75,
    };
  }
  return { fill: fillBase, stroke: strokeBase, lineWidth: lwBase };
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
 * @param {{ normalizeUnderscores?: boolean }} [opts] When true (default), Neo4j-style `HAS_X` becomes `HAS X`.
 *   Set false for backend `displayType` strings so literal underscores are preserved.
 * @returns {string}
 */
export function edgeTypeCanvasLabel(edgeType, opts = {}) {
  const normalizeUnderscores = opts.normalizeUnderscores !== false;
  let t = edgeType == null ? "" : String(edgeType).trim();
  if (normalizeUnderscores) t = t.replace(/_/g, " ");
  return truncateCanvasLabel(t, EDGE_LABEL_MAX);
}

/**
 * Edge label for canvas / React Flow: prefers `displayType`, else `type` with underscore spacing.
 *
 * @param {{ displayType?: string, type?: string }} edge
 * @returns {string}
 */
export function edgeTypeCanvasLabelFromEdge(edge) {
  const displayRaw = edge?.displayType != null ? String(edge.displayType).trim() : "";
  const resolved = displayRaw || edge?.type;
  return edgeTypeCanvasLabel(resolved, { normalizeUnderscores: !displayRaw });
}
