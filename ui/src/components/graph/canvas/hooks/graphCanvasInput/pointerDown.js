import { flushSync } from "react-dom";

import { hitTestNodeScreen } from "../../graphCanvasDraw.js";
import { dispatchGraphCanvasPointerDown } from "../../graphCanvasPointerEvents.js";
import { screenToWorld } from "../../graphCanvasTransform.js";
import { writeSimNodeWorldPosition } from "../../graphCanvasSimBuffer.js";

import { buildNodeHitTestScreenOpts } from "./hitTestContext.js";

/**
 * Primary-button pointer down: start node drag (force buffer) or canvas pan session.
 *
 * @param {object} ctx
 * @param {import("react").RefObject<HTMLCanvasElement | null>} ctx.canvasRef
 * @param {import("react").MutableRefObject<import("../../model/graphSimulationAdapter.js").SimNode[]>} ctx.simNodesRef
 * @param {() => Map<string, { x: number; y: number }>} ctx.getPositionsForFrame
 * @param {{ nodes: unknown[] }} ctx.graph
 * @param {import("react").MutableRefObject<{ scale: number; tx: number; ty: number }>} ctx.transformRef
 * @param {(node: unknown) => string | null} ctx.resolveNodeCanvasLabel
 * @param {string} ctx.graphColorBy
 * @param {string} ctx.hoveredNodeId
 * @param {boolean} ctx.searchActive
 * @param {unknown} ctx.searchMatchSet
 * @param {string} ctx.selectedNodeId
 * @param {string} ctx.canvasLabelMode
 * @param {import("react").MutableRefObject<Set<string> | null> | null} [ctx.activeForLabelSetRef]
 * @param {string} ctx.layoutMode
 * @param {(mode: string) => void} [ctx.onCanvasLayoutModeChange]
 * @param {import("react").MutableRefObject<{ id: string; x: number; y: number } | null>} ctx.draggedNodePositionRef
 * @param {import("react").MutableRefObject<{ active: boolean; moved: boolean; nodeId: string; startX: number; startY: number; pointerId: number | null }>} ctx.nodeDragRef
 * @param {import("react").MutableRefObject<{ active: boolean; moved: boolean; startX: number; startY: number; startTx: number; startTy: number; pointerId: number | null }>} ctx.dragRef
 * @param {() => void} ctx.invokeCanvasRedraw
 * @param {EventTarget | null | undefined} ctx.pointerBus
 * @param {PointerEvent} ev
 */
export function graphCanvasInputPointerDown(ctx, ev) {
  if (ev.button !== 0) return;
  const canvas = ctx.canvasRef.current;
  if (!canvas) return;
  dispatchGraphCanvasPointerDown(ctx.pointerBus);
  const rect = canvas.getBoundingClientRect();
  const x = ev.clientX - rect.left;
  const y = ev.clientY - rect.top;
  const { scale, tx, ty } = ctx.transformRef.current;
  if (ctx.simNodesRef.current.length > 0) {
    const posMap = ctx.getPositionsForFrame();
    const hitOpts = buildNodeHitTestScreenOpts({
      graphColorBy: ctx.graphColorBy,
      graph: ctx.graph,
      searchActive: ctx.searchActive,
      searchMatchSet: ctx.searchMatchSet,
      selectedNodeId: ctx.selectedNodeId,
      hoveredNodeId: ctx.hoveredNodeId,
      canvasLabelMode: ctx.canvasLabelMode,
      activeForLabelSetRef: ctx.activeForLabelSetRef,
    });
    const nodeId = hitTestNodeScreen(x, y, ctx.graph.nodes, posMap, ctx.transformRef.current, ctx.resolveNodeCanvasLabel, hitOpts);
    if (nodeId) {
      if (ctx.layoutMode === "circle" && ctx.onCanvasLayoutModeChange) flushSync(() => ctx.onCanvasLayoutModeChange("force"));
      const world = screenToWorld(x, y, scale, tx, ty);
      canvas.setPointerCapture(ev.pointerId);
      ctx.nodeDragRef.current = { active: true, moved: false, nodeId, startX: x, startY: y, pointerId: ev.pointerId };
      ctx.draggedNodePositionRef.current = { id: nodeId, x: world.x, y: world.y };
      writeSimNodeWorldPosition(ctx.simNodesRef.current, nodeId, world.x, world.y);
      ctx.invokeCanvasRedraw();
      return;
    }
  }
  canvas.setPointerCapture(ev.pointerId);
  ctx.dragRef.current = { active: true, moved: false, startX: x, startY: y, startTx: tx, startTy: ty, pointerId: ev.pointerId };
}
