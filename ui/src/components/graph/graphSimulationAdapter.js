/**
 * Builds force-simulation state from a normalized, UI-capped graph.
 */

import { computeWorldLayout, worldRadiusForNodeCount } from "./graphCanvasTransform.js";

/**
 * @typedef {{ id: string, x: number, y: number, vx: number, vy: number, type: string, label: string }} SimNode
 * @typedef {{ id: string, source: string, target: string, type: string }} SimLink
 */

/**
 * @param {{ nodes: Array<{ id: string, label?: string, type?: string }>, edges: Array<{ id: string, source: string, target: string, type?: string }> }} graph
 * @param {{ jitterWorld?: number }} [options] If `jitterWorld` &gt; 0, per-node random offset in world units (osint-style restart spread).
 * @returns {{ nodes: SimNode[], links: SimLink[] }}
 */
export function buildSimulationState(graph, options = {}) {
  const rawNodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
  const rawEdges = Array.isArray(graph?.edges) ? graph.edges : [];
  const wr = worldRadiusForNodeCount(rawNodes.length);
  const pos = computeWorldLayout(rawNodes, wr);
  const jitter = typeof options.jitterWorld === "number" && options.jitterWorld > 0 ? options.jitterWorld : 0;

  const nodes = rawNodes.map((n) => {
    const p = pos.get(n.id) || { x: 0, y: 0 };
    const jx = jitter > 0 ? (Math.random() - 0.5) * 2 * jitter : 0;
    const jy = jitter > 0 ? (Math.random() - 0.5) * 2 * jitter : 0;
    return {
      id: n.id,
      x: p.x + jx,
      y: p.y + jy,
      vx: 0,
      vy: 0,
      type: n.type == null ? "Node" : String(n.type),
      label:
        n.displayLabel != null && String(n.displayLabel).trim()
          ? String(n.displayLabel)
          : n.label == null
            ? String(n.id)
            : String(n.label),
    };
  });

  const links = rawEdges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    type: e.type == null ? "edge" : String(e.type),
  }));

  return { nodes, links };
}
