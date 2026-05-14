import { dispatchGraphCanvasPointerUp } from "../../graphCanvasPointerEvents.js";

import { resolveGraphCanvasClickSelection } from "./clickSelection.js";

/**
 * Pointer up: end node drag (pin / click) or pan (click selection vs hover refresh).
 *
 * @param {object} ctx
 * @param {import("react").RefObject<HTMLCanvasElement | null>} ctx.canvasRef
 * @param {import("react").MutableRefObject<{ active: boolean; moved: boolean; nodeId: string; startX: number; startY: number; pointerId: number | null }>} ctx.nodeDragRef
 * @param {import("react").MutableRefObject<{ active: boolean; moved: boolean; startX: number; startY: number; startTx: number; startTy: number; pointerId: number | null }>} ctx.dragRef
 * @param {import("react").MutableRefObject<{ id: string; x: number; y: number } | null>} ctx.draggedNodePositionRef
 * @param {import("react").MutableRefObject<import("../../model/graphSimulationAdapter.js").SimNode[]>} ctx.simNodesRef
 * @param {import("react").MutableRefObject<Set<string>>} ctx.fixedNodesRef
 * @param {boolean} ctx.isSimulationStable
 * @param {import("react").Dispatch<import("react").SetStateAction<boolean>>} ctx.setIsSimulationStable
 * @param {() => void} ctx.bumpPhysicsReheat
 * @param {(nodes: import("../../model/graphSimulationAdapter.js").SimNode[]) => void} ctx.setSimNodes
 * @param {import("react").Dispatch<import("react").SetStateAction<number>>} ctx.setPinnedNodeCount
 * @param {() => void} ctx.invokeCanvasRedraw
 * @param {() => Map<string, { x: number; y: number }>} ctx.getPositionsForFrame
 * @param {{ nodes: unknown[]; edges: unknown[] }} ctx.graph
 * @param {import("react").MutableRefObject<{ scale: number; tx: number; ty: number }>} ctx.transformRef
 * @param {(node: unknown) => string | null} ctx.resolveNodeCanvasLabel
 * @param {string} ctx.graphColorBy
 * @param {string} ctx.hoveredNodeId
 * @param {boolean} ctx.searchActive
 * @param {unknown} ctx.searchMatchSet
 * @param {string} ctx.selectedNodeId
 * @param {string} ctx.canvasLabelMode
 * @param {import("react").MutableRefObject<Set<string> | null> | null} [ctx.activeForLabelSetRef]
 * @param {(nodeId: string) => void} [ctx.onNodeClick]
 * @param {(edgeId: string) => void} [ctx.onEdgeClick]
 * @param {() => void} [ctx.onCanvasClick]
 * @param {(clientX: number, clientY: number) => void} ctx.queueHoverPick
 * @param {EventTarget | null | undefined} ctx.pointerBus
 * @param {PointerEvent} ev
 */
export function graphCanvasInputPointerUp(ctx, ev) {
  try {
    const canvas = ctx.canvasRef.current;
    const nd = ctx.nodeDragRef.current;
    if (nd.active) {
      try {
        canvas?.releasePointerCapture(ev.pointerId);
      } catch {
        /* ignore */
      }
      const { nodeId, moved } = nd;
      const pinAfterDrop = moved && ctx.isSimulationStable;
      ctx.nodeDragRef.current = { active: false, moved: false, nodeId: "", startX: 0, startY: 0, pointerId: null };
      ctx.draggedNodePositionRef.current = null;
      if (moved) {
        ctx.setIsSimulationStable(false);
        ctx.bumpPhysicsReheat();
      }
      if (pinAfterDrop) {
        ctx.fixedNodesRef.current.add(nodeId);
        ctx.setPinnedNodeCount(ctx.fixedNodesRef.current.size);
      }
      if (moved) {
        ctx.setSimNodes(ctx.simNodesRef.current.map((n) => ({ ...n })));
        ctx.invokeCanvasRedraw();
      }
      if (!moved) queueMicrotask(() => ctx.onNodeClick?.(nodeId));
      ctx.queueHoverPick(ev.clientX, ev.clientY);
      return;
    }
    const d = ctx.dragRef.current;
    if (!d.active) return;
    try {
      canvas?.releasePointerCapture(ev.pointerId);
    } catch {
      /* ignore */
    }
    ctx.dragRef.current = { ...d, active: false, pointerId: null };
    if (!d.moved) {
      const pick = resolveGraphCanvasClickSelection(
        {
          canvasRef: ctx.canvasRef,
          getPositionsForFrame: ctx.getPositionsForFrame,
          graph: ctx.graph,
          transformRef: ctx.transformRef,
          resolveNodeCanvasLabel: ctx.resolveNodeCanvasLabel,
          graphColorBy: ctx.graphColorBy,
          hoveredNodeId: ctx.hoveredNodeId,
          searchActive: ctx.searchActive,
          searchMatchSet: ctx.searchMatchSet,
          selectedNodeId: ctx.selectedNodeId,
          canvasLabelMode: ctx.canvasLabelMode,
          activeForLabelSetRef: ctx.activeForLabelSetRef,
        },
        ev.clientX,
        ev.clientY,
      );
      if (pick.kind === "node") {
        queueMicrotask(() => ctx.onNodeClick?.(pick.nodeId));
        return;
      }
      if (pick.kind === "edge") {
        queueMicrotask(() => ctx.onEdgeClick?.(pick.edgeId));
        return;
      }
      queueMicrotask(() => ctx.onCanvasClick?.());
    } else {
      ctx.queueHoverPick(ev.clientX, ev.clientY);
    }
  } finally {
    dispatchGraphCanvasPointerUp(ctx.pointerBus);
  }
}
