import { screenToWorld } from "../../graphCanvasTransform.js";
import { writeSimNodeWorldPosition } from "../../graphCanvasSimBuffer.js";

import { DRAG_THRESHOLD_PX } from "./constants.js";

/**
 * @param {object} ctx
 * @param {import("react").RefObject<HTMLCanvasElement | null>} ctx.canvasRef
 * @param {import("react").MutableRefObject<{ active: boolean; moved: boolean; nodeId: string; startX: number; startY: number; pointerId: number | null }>} ctx.nodeDragRef
 * @param {import("react").MutableRefObject<{ active: boolean; moved: boolean; startX: number; startY: number; startTx: number; startTy: number; pointerId: number | null }>} ctx.dragRef
 * @param {import("react").MutableRefObject<{ id: string; x: number; y: number } | null>} ctx.draggedNodePositionRef
 * @param {import("react").MutableRefObject<import("../../model/graphSimulationAdapter.js").SimNode[]>} ctx.simNodesRef
 * @param {import("react").MutableRefObject<{ scale: number; tx: number; ty: number }>} ctx.transformRef
 * @param {(t: { scale: number; tx: number; ty: number }) => void} ctx.setTransform
 * @param {import("react").Dispatch<import("react").SetStateAction<boolean>>} ctx.setIsSimulationStable
 * @param {() => void} ctx.bumpPhysicsReheat
 * @param {import("react").Dispatch<import("react").SetStateAction<string>>} ctx.setHoveredNodeId
 * @param {import("react").Dispatch<import("react").SetStateAction<string>>} ctx.setHoveredEdgeId
 * @param {import("react").Dispatch<import("react").SetStateAction<string>>} ctx.setCanvasCursor
 * @param {(clientX: number, clientY: number) => void} ctx.queueHoverPick
 * @param {() => void} ctx.invokeCanvasRedraw
 * @param {PointerEvent} ev
 */
export function graphCanvasInputPointerMove(ctx, ev) {
  const canvas = ctx.canvasRef.current;
  if (!canvas) return;
  const nd = ctx.nodeDragRef.current;
  if (nd.active) {
    const rect = canvas.getBoundingClientRect();
    const x = ev.clientX - rect.left;
    const y = ev.clientY - rect.top;
    const dx = x - nd.startX;
    const dy = y - nd.startY;
    if (!nd.moved && dx * dx + dy * dy > DRAG_THRESHOLD_PX * DRAG_THRESHOLD_PX) {
      nd.moved = true;
      ctx.setHoveredNodeId("");
      ctx.setHoveredEdgeId("");
      ctx.setCanvasCursor("grabbing");
      ctx.setIsSimulationStable(false);
      ctx.bumpPhysicsReheat();
    }
    const world = screenToWorld(x, y, ctx.transformRef.current.scale, ctx.transformRef.current.tx, ctx.transformRef.current.ty);
    ctx.draggedNodePositionRef.current = { id: nd.nodeId, x: world.x, y: world.y };
    writeSimNodeWorldPosition(ctx.simNodesRef.current, nd.nodeId, world.x, world.y);
    ctx.invokeCanvasRedraw();
    return;
  }
  const d = ctx.dragRef.current;
  if (d.active) {
    const rect = canvas.getBoundingClientRect();
    const x = ev.clientX - rect.left;
    const y = ev.clientY - rect.top;
    const dx = x - d.startX;
    const dy = y - d.startY;
    if (!d.moved && dx * dx + dy * dy > DRAG_THRESHOLD_PX * DRAG_THRESHOLD_PX) {
      d.moved = true;
      ctx.setHoveredNodeId("");
      ctx.setHoveredEdgeId("");
      ctx.setCanvasCursor("grabbing");
    }
    if (d.moved) {
      const next = { scale: ctx.transformRef.current.scale, tx: d.startTx + dx, ty: d.startTy + dy };
      ctx.transformRef.current = next;
      ctx.setTransform(next);
    }
    return;
  }
  ctx.queueHoverPick(ev.clientX, ev.clientY);
}
