import { useMemo } from "react";

/**
 * Undirected 1-hop adjacency for graph edges. O(E) build; neighborhood lookups O(deg).
 *
 * @param {Array<{ source?: string, target?: string }>} edges
 * @returns {Map<string, Set<string>>}
 */
export function buildGraphAdjacencyMap(edges) {
  /** @type {Map<string, Set<string>>} */
  const map = new Map();
  if (!Array.isArray(edges)) return map;
  for (const edge of edges) {
    const s = String(edge?.source ?? "");
    const t = String(edge?.target ?? "");
    if (!s || !t) continue;
    let aSet = map.get(s);
    if (!aSet) {
      aSet = new Set();
      map.set(s, aSet);
    }
    let bSet = map.get(t);
    if (!bSet) {
      bSet = new Set();
      map.set(t, bSet);
    }
    aSet.add(t);
    bSet.add(s);
  }
  return map;
}

/**
 * @param {Array<{ source?: string, target?: string }>} edges
 */
export function useGraphAdjacency(edges) {
  return useMemo(() => buildGraphAdjacencyMap(edges), [edges]);
}
