import { CANVAS_MARGIN } from "../../components/graph/canvas/physics/simConstants.js";

export const WORLD_SCALE = 3;
export const BOUNDS_SMOOTHING = 0.15;

export function lerp(a, b, t) {
  return a + (b - a) * t;
}

/**
 * @param {{ width: number, height: number }} canvasSize
 * @returns {(nodeList: Array<{ x: number, y: number }> | null | undefined) => {
 *   minX: number,
 *   maxX: number,
 *   minY: number,
 *   maxY: number,
 *   width: number,
 *   height: number,
 * }}
 */
export function createWorldBoundsCalculator(canvasSize) {
  const MIN_WORLD_SPAN = Math.max(canvasSize.width, canvasSize.height) * WORLD_SCALE;

  return (nodeList) => {
    if (!nodeList || nodeList.length === 0) {
      const halfSpan = MIN_WORLD_SPAN / 2 + CANVAS_MARGIN * 2;
      return {
        minX: -halfSpan,
        maxX: halfSpan,
        minY: -halfSpan,
        maxY: halfSpan,
        width: halfSpan * 2,
        height: halfSpan * 2,
      };
    }

    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;

    nodeList.forEach((node) => {
      if (node.x < minX) minX = node.x;
      if (node.x > maxX) maxX = node.x;
      if (node.y < minY) minY = node.y;
      if (node.y > maxY) maxY = node.y;
    });

    const spanX = Math.max(maxX - minX, MIN_WORLD_SPAN);
    const spanY = Math.max(maxY - minY, MIN_WORLD_SPAN);
    const padding = Math.max(CANVAS_MARGIN * 2, Math.max(spanX, spanY) * 0.15);
    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;
    const halfX = spanX / 2 + padding;
    const halfY = spanY / 2 + padding;

    return {
      minX: centerX - halfX,
      maxX: centerX + halfX,
      minY: centerY - halfY,
      maxY: centerY + halfY,
      width: halfX * 2,
      height: halfY * 2,
    };
  };
}
