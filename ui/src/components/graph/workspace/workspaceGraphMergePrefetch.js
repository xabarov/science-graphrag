/**
 * @param {object | null | undefined} base
 * @param {object | null | undefined} extra
 * @returns {object}
 */
export function mergeWorkspaceRawGraph(base, extra) {
  if (!base || typeof base !== "object") return extra;
  const nmap = new Map();
  for (const n of /** @type {unknown[]} */ (base.nodes || [])) {
    const id = String((n && typeof n === "object" ? n.id : "") || "");
    if (id) nmap.set(id, n);
  }
  for (const n of /** @type {unknown[]} */ (extra.nodes || [])) {
    const id = String((n && typeof n === "object" ? n.id : "") || "");
    if (id) nmap.set(id, n);
  }
  const emap = new Map();
  const ekey = (e) => {
    const o = e && typeof e === "object" ? e : {};
    return o.id || `${o.source}|${o.type}|${o.target}`;
  };
  for (const e of /** @type {unknown[]} */ (base.edges || [])) emap.set(ekey(e), e);
  for (const e of /** @type {unknown[]} */ (extra.edges || [])) emap.set(ekey(e), e);
  return {
    ...base,
    nodes: [...nmap.values()],
    edges: [...emap.values()],
    meta: { ...(typeof base.meta === "object" ? base.meta : {}), ...(typeof extra.meta === "object" ? extra.meta : {}) },
  };
}

/**
 * Legacy hook: server neighbor aggregation (GR8) is disabled — no Aggregator placeholders to resolve.
 * Kept as a stable import for {@link useGraphWorkspaceData}.
 *
 * @param {object} initialRaw
 * @param {Set<string>} [persistentSeen]
 * @returns {Promise<object>}
 */
export async function prefetchAuthorAggregatorExpansions(initialRaw, persistentSeen) {
  void persistentSeen;
  return initialRaw;
}
