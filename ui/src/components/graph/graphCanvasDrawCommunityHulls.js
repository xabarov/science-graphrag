import { polygonHull } from "d3-polygon";

import { worldToScreen } from "./graphCanvasTransform.js";

const DEFAULT_MAX_HULLS = 24;
const WORLD_PAD = 24;

/** Below this canvas scale, hull center labels are omitted (hull fill/stroke still drawn). */
const HULL_LABEL_MIN_SCALE = 0.24;

/** Skip hull labels when projected hull bounding box area is below this (px²). */
const HULL_LABEL_MIN_SCREEN_AREA = 3800;

/** Larger hulls on screen get slightly weaker fill before overlap (GR-COM-2). */
const HULL_FILL_LARGE_AREA_REF = 220000;

/** Gain for overlap pressure -> fill alpha multiplier (higher = more attenuation in dense overlap). */
const HULL_OVERLAP_ATTENUATION_GAIN = 0.42;

/** Minimum fill alpha multiplier (never fully hide hull context). */
const HULL_FILL_ALPHA_MUL_MIN = 0.32;

/** When fill is attenuated, nudge stroke width for readability. */
const HULL_STROKE_BOOST_THRESHOLD = 0.78;

/**
 * @param {{ minX: number, minY: number, maxX: number, maxY: number }} a
 * @param {{ minX: number, minY: number, maxX: number, maxY: number }} b
 * @returns {number}
 */
export function rectIntersectionArea(a, b) {
  const ix0 = Math.max(a.minX, b.minX);
  const iy0 = Math.max(a.minY, b.minY);
  const ix1 = Math.min(a.maxX, b.maxX);
  const iy1 = Math.min(a.maxY, b.maxY);
  const w = Math.max(0, ix1 - ix0);
  const h = Math.max(0, iy1 - iy0);
  return w * h;
}

/**
 * Rough overlap pressure for one hull vs others (axis-aligned bbox overlap, px²).
 *
 * @param {{ minX: number, minY: number, maxX: number, maxY: number, area: number }} box
 * @param {Array<{ minX: number, minY: number, maxX: number, maxY: number, area: number }>} all
 * @param {number} selfIndex
 * @returns {number}
 */
export function hullOverlapPressure(box, all, selfIndex) {
  if (!box || !Array.isArray(all) || all.length < 2) return 0;
  let sum = 0;
  const denom = Math.max(box.area, 1);
  for (let j = 0; j < all.length; j += 1) {
    if (j === selfIndex) continue;
    const b = all[j];
    if (!b) continue;
    const inter = rectIntersectionArea(box, b);
    if (inter <= 0) continue;
    const norm = inter / denom;
    sum += norm;
  }
  return sum;
}

/**
 * @param {number} overlapPressure sum of interArea/selfArea vs other hull bboxes
 * @param {number} screenArea self bbox area px²
 * @returns {number} multiply into hull fill alpha (0..1)
 */
export function hullFillAlphaMultiplier(overlapPressure, screenArea) {
  const p = typeof overlapPressure === "number" && Number.isFinite(overlapPressure) ? Math.max(0, overlapPressure) : 0;
  const area = typeof screenArea === "number" && Number.isFinite(screenArea) ? Math.max(0, screenArea) : 0;
  const sizeSoft = 1 / (1 + Math.max(0, area) / HULL_FILL_LARGE_AREA_REF);
  const overlapSoft = 1 / (1 + HULL_OVERLAP_ATTENUATION_GAIN * p);
  const mul = overlapSoft * (0.55 + 0.45 * sizeSoft);
  return Math.min(1, Math.max(HULL_FILL_ALPHA_MUL_MIN, mul));
}

/**
 * @param {Array<[number, number]>} ring closed or open ring in world space
 * @param {number} pad
 * @returns {Array<[number, number]>}
 */
function expandHullFromCentroid(ring, pad) {
  if (!ring || ring.length < 3) return ring;
  let cx = 0;
  let cy = 0;
  ring.forEach(([x, y]) => {
    cx += x;
    cy += y;
  });
  cx /= ring.length;
  cy /= ring.length;
  let meanDist = 0;
  ring.forEach(([x, y]) => {
    const dx = x - cx;
    const dy = y - cy;
    meanDist += Math.sqrt(dx * dx + dy * dy);
  });
  meanDist /= ring.length;
  const scale = 1 + pad / Math.max(meanDist, 1e-6);
  return ring.map(([x, y]) => {
    const dx = x - cx;
    const dy = y - cy;
    return [cx + dx * scale, cy + dy * scale];
  });
}

/**
 * @param {CanvasRenderingContext2D} ctx
 * @param {Iterable<object>} nodes
 * @param {Map<string, { x: number, y: number }>} positions world positions
 * @param {{ scale: number, tx: number, ty: number }} transform
 * @param {Map<string, string>} nodeCommunityMap
 * @param {Map<string, { hullFill: string, hullStroke: string }>} communityColorStyleMap
 * @param {{ appearance?: "light" | "dark", maxHulls?: number, communityRanks?: Map<string, number>, formatHullLabel?: (rankOneBased: number, nodeCount: number) => string }} [opts]
 */
export function drawCommunityHulls(ctx, nodes, positions, transform, nodeCommunityMap, communityColorStyleMap, opts = {}) {
  const light = String(opts.appearance || "dark") === "light";
  const maxHulls = typeof opts.maxHulls === "number" && opts.maxHulls > 0 ? opts.maxHulls : DEFAULT_MAX_HULLS;
  const ranks = opts.communityRanks instanceof Map ? opts.communityRanks : null;

  const byC = new Map();
  (nodes || []).forEach((n) => {
    if (!n || n.id == null) return;
    const id = String(n.id);
    const cid = nodeCommunityMap.get(id);
    if (cid == null) return;
    const c = String(cid);
    const pw = positions.get(id);
    if (!pw) return;
    if (!byC.has(c)) byC.set(c, []);
    byC.get(c).push([pw.x, pw.y]);
  });

  const candidates = [...byC.entries()]
    .filter(([, pts]) => pts.length >= 3)
    .map(([cid, pts]) => ({
      cid,
      pts,
      count: pts.length,
      rank: ranks?.get(cid) ?? 999999,
    }))
    .sort((a, b) => a.rank - b.rank || b.count - a.count || String(a.cid).localeCompare(String(b.cid)));

  const slice = candidates.slice(0, maxHulls);

  /** @type {Array<{ entry: typeof candidates[0], expanded: Array<[number, number]>, box: { minX: number, minY: number, maxX: number, maxY: number, area: number, cx: number, cy: number } }>} */
  const prepared = [];
  slice.forEach((entry) => {
    const hull = polygonHull(entry.pts);
    if (!hull || hull.length < 3) return;
    const expanded = expandHullFromCentroid(hull, WORLD_PAD);
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    expanded.forEach(([wx, wy]) => {
      const { x, y } = worldToScreen(wx, wy, transform.scale, transform.tx, transform.ty);
      minX = Math.min(minX, x);
      minY = Math.min(minY, y);
      maxX = Math.max(maxX, x);
      maxY = Math.max(maxY, y);
    });
    const bw = maxX - minX;
    const bh = maxY - minY;
    const area = Math.max(0, bw) * Math.max(0, bh);
    prepared.push({
      entry,
      expanded,
      box: {
        minX,
        minY,
        maxX,
        maxY,
        area,
        cx: (minX + maxX) / 2,
        cy: (minY + maxY) / 2,
      },
    });
  });

  const boxes = prepared.map((p) => p.box);

  prepared.forEach((prep, hullIdx) => {
    const { entry, expanded, box } = prep;
    const style = communityColorStyleMap.get(entry.cid) || {};
    const fill = style.hullFill || "rgba(148, 163, 184, 0.06)";
    const stroke = style.hullStroke || "rgba(203, 213, 225, 0.22)";
    const pressure = hullOverlapPressure(box, boxes, hullIdx);
    const fillAlphaMul = hullFillAlphaMultiplier(pressure, box.area);

    ctx.beginPath();
    expanded.forEach(([wx, wy], i) => {
      const { x, y } = worldToScreen(wx, wy, transform.scale, transform.tx, transform.ty);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.closePath();
    ctx.save();
    ctx.globalAlpha = fillAlphaMul;
    ctx.fillStyle = fill;
    ctx.fill();
    ctx.restore();
    ctx.strokeStyle = stroke;
    ctx.lineWidth = fillAlphaMul < HULL_STROKE_BOOST_THRESHOLD ? 1.25 : 1;
    ctx.stroke();

    let cxw = 0;
    let cyw = 0;
    expanded.forEach(([wx, wy]) => {
      cxw += wx;
      cyw += wy;
    });
    cxw /= expanded.length;
    cyw /= expanded.length;
    const center = worldToScreen(cxw, cyw, transform.scale, transform.tx, transform.ty);
    const rankOneBased = typeof entry.rank === "number" && entry.rank < 999999 ? entry.rank + 1 : hullIdx + 1;
    const format =
      typeof opts.formatHullLabel === "function"
        ? opts.formatHullLabel
        : (rank, count) => `Cluster #${rank} · ${count}`;
    const label = format(rankOneBased, entry.count);

    const screenArea = box.area;
    const sc = Number(transform.scale);
    const scaleOk = Number.isFinite(sc) && sc >= HULL_LABEL_MIN_SCALE;
    const areaOk = screenArea >= HULL_LABEL_MIN_SCREEN_AREA;
    if (!scaleOk || !areaOk) {
      return;
    }

    const labelAlpha = Math.min(0.92, Math.max(0.38, (sc - HULL_LABEL_MIN_SCALE) / 0.55));
    ctx.save();
    ctx.globalAlpha = labelAlpha;
    ctx.font = '600 10px Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillStyle = light ? "rgba(15,23,42,0.82)" : "rgba(255,255,255,0.72)";
    ctx.strokeStyle = light ? "rgba(255,255,255,0.85)" : "rgba(0,0,0,0.35)";
    ctx.lineWidth = 3;
    ctx.strokeText(label, center.x, center.y);
    ctx.fillText(label, center.x, center.y);
    ctx.restore();
  });
}
