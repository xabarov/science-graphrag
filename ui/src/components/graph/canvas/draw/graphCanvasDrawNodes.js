import { getScienceGraphNodeStyle } from "../graphCanvasStyle.js";
import { worldToScreen } from "../graphCanvasTransform.js";
import { NODE_RADIUS } from "./graphCanvasDrawConstants.js";
import { strokeAtHalfAlpha } from "./graphCanvasDrawColor.js";

export function drawNodes(ctx, nodes, positions, transform, styleMap = {}, drawOpts = {}) {
  const appearance = String(drawOpts.appearance || "dark") === "light" ? "light" : "dark";
  const colorBy = drawOpts.colorBy === "community" ? "community" : "type";
  const nodeCommunityMap = drawOpts.nodeCommunityMap instanceof Map ? drawOpts.nodeCommunityMap : null;
  const communityColorStyleMap =
    drawOpts.communityColorStyleMap instanceof Map ? drawOpts.communityColorStyleMap : null;
  const { scale, tx, ty } = transform;
  for (const node of nodes) {
    const pw = positions.get(node.id);
    if (!pw) continue;
    const p = worldToScreen(pw.x, pw.y, scale, tx, ty);
    const sid = String(node.id || "");
    const sm = styleMap[sid] || {};
    const style = getScienceGraphNodeStyle(node.type, {
      selected: Boolean(sm.selected),
      hovered: Boolean(sm.hovered),
      workspaceMembership: node.workspaceMembership,
      nodeKind: node.nodeKind,
      searchDim: Boolean(sm.searchDim),
      focusDim: Boolean(sm.focusDim),
      appearance,
    });
    let fillStyle = style.fill;
    let strokeStyle = style.stroke;
    const skipCommunityFill = Boolean(sm.selected || sm.hovered || sm.searchDim || sm.focusDim);
    if (colorBy === "community" && nodeCommunityMap && communityColorStyleMap && !skipCommunityFill) {
      const cid = nodeCommunityMap.get(sid);
      if (cid != null) {
        const cs = communityColorStyleMap.get(String(cid));
        if (cs?.fill) fillStyle = cs.fill;
        strokeStyle = strokeAtHalfAlpha(style.stroke);
      }
    }
    ctx.beginPath();
    ctx.arc(p.x, p.y, NODE_RADIUS, 0, 2 * Math.PI);
    ctx.fillStyle = fillStyle;
    ctx.fill();
    ctx.strokeStyle = strokeStyle;
    ctx.lineWidth = style.lineWidth;
    if (Array.isArray(style.strokeDash) && style.strokeDash.length > 0) ctx.setLineDash(style.strokeDash);
    ctx.stroke();
    ctx.setLineDash([]);
    if (node.nodeKind === "Aggregator") {
      const badge = node.raw?.aggregation_hints?.count;
      const badgeText = Number.isFinite(Number(badge)) ? `+${Number(badge)}` : "+";
      ctx.font = '700 11px Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillStyle = "rgba(129, 140, 248, 0.95)";
      ctx.fillText(badgeText, p.x, p.y);
    }
  }
}
