/**
 * Graph helpers for route state and lightweight visualization.
 */

/**
 * @param {unknown} value
 * @returns {string}
 */
export function normalizeGraphNodeId(value) {
  if (value == null) return "";
  return String(value).trim();
}

/**
 * @param {unknown} value
 * @returns {string}
 */
export function normalizeGraphEdgeId(value) {
  if (value == null) return "";
  return String(value).trim();
}

/**
 * @param {Record<string, unknown>} obj
 * @param {string[]} keys snake_case and camelCase variants from API
 * @param {string} fallback
 */
function pickStringField(obj, keys, fallback) {
  for (const k of keys) {
    const v = obj[k];
    if (v == null) continue;
    const s = String(v).trim();
    if (s) return s;
  }
  return fallback;
}

/**
 * @param {unknown} v
 * @returns {Record<string, unknown>}
 */
function pickPropertiesObject(v) {
  if (v && typeof v === "object" && !Array.isArray(v)) {
    return /** @type {Record<string, unknown>} */ (v);
  }
  return {};
}

/**
 * Workspace container exists in Neo4j and API payloads but is redundant in the graph UI
 * (every work already belongs to the current workspace context).
 *
 * @param {{ type: string, nodeKind: string }} node Normalized node from {@link normalizeGraphPayload} mapping step
 * @returns {boolean}
 */
function isUiHiddenWorkspaceNode(node) {
  const t = String(node.type || "").trim().toLowerCase();
  const k = String(node.nodeKind || "").trim().toLowerCase();
  return t === "workspace" || k === "workspace";
}

/**
 * @param {unknown} raw
 * @returns {{
 *   workId: string,
 *   nodes: Array<object>,
 *   edges: Array<object>,
 *   meta: object,
 *   nodeCount: number,
 *   edgeCount: number,
 *   selectedNodeId: string,
 *   warnings: string[],
 * }}
 */
export function normalizeGraphPayload(raw) {
  const warnings = [];
  const payload = raw && typeof raw === "object" ? raw : {};
  const rawNodes = Array.isArray(payload.nodes) ? payload.nodes : [];
  const rawEdges = Array.isArray(payload.edges) ? payload.edges : [];
  const meta = payload.meta && typeof payload.meta === "object" ? payload.meta : {};

  const idUsage = new Map();
  const mappedNodes = rawNodes.map((node, index) => {
    const baseId = node?.id == null ? `node-${index}` : String(node.id);
    const seen = idUsage.get(baseId) ?? 0;
    idUsage.set(baseId, seen + 1);
    const id = seen === 0 ? baseId : `${baseId}__dup${seen}`;
    if (seen > 0) {
      warnings.push(
        `Duplicate node id "${baseId}" was reassigned to "${id}" (first occurrence keeps "${baseId}").`,
      );
    }
    const n = node && typeof node === "object" ? /** @type {Record<string, unknown>} */ (node) : {};
    const label = n.label == null ? String(n.id ?? `node-${index}`) : String(n.label);
    const type = n.type == null ? "Node" : String(n.type);
    const displayLabel = pickStringField(n, ["display_label", "displayLabel"], label);
    const subtitle = pickStringField(n, ["subtitle"], "");
    const nodeKind = pickStringField(n, ["node_kind", "nodeKind"], type);
    const properties = { ...pickPropertiesObject(n.properties) };
    const workspaceMembership = pickStringField(
      n,
      ["workspace_membership", "workspaceMembership"],
      "",
    );
    const ic = n.internal_cite_count ?? n.internalCiteCount;
    const ec = n.external_cite_count ?? n.externalCiteCount;
    const internalCiteCount = typeof ic === "number" && Number.isFinite(ic) ? ic : undefined;
    const externalCiteCount = typeof ec === "number" && Number.isFinite(ec) ? ec : undefined;
    return {
      id,
      label,
      type,
      displayLabel,
      subtitle,
      nodeKind,
      properties,
      workspaceMembership,
      internalCiteCount,
      externalCiteCount,
      raw: n,
    };
  });

  const hiddenWorkspaceIds = new Set(
    mappedNodes.filter(isUiHiddenWorkspaceNode).map((n) => n.id),
  );
  const nodes = mappedNodes.filter((n) => !isUiHiddenWorkspaceNode(n));

  const nodeIdSet = new Set(nodes.map((n) => n.id));

  const normalizedEdges = rawEdges.map((edge, index) => {
    const e = edge && typeof edge === "object" ? /** @type {Record<string, unknown>} */ (edge) : {};
    const src = e.source == null ? "" : String(e.source);
    const tgt = e.target == null ? "" : String(e.target);
    const typ = e.type == null ? "edge" : String(e.type);
    const eid = e.id == null ? `edge-${index}` : String(e.id);
    const displayType = pickStringField(e, ["display_type", "displayType"], typ.replace(/_/g, " ") || "related");
    const sourceLabel = pickStringField(e, ["source_label", "sourceLabel"], "");
    const targetLabel = pickStringField(e, ["target_label", "targetLabel"], "");
    const summary = pickStringField(e, ["summary"], "");
    const direction = pickStringField(e, ["direction"], "");
    return {
      id: eid,
      source: src,
      target: tgt,
      type: typ,
      displayType,
      sourceLabel,
      targetLabel,
      summary,
      direction,
      raw: e,
    };
  });

  const edges = [];
  let orphanCount = 0;
  for (const edge of normalizedEdges) {
    if (hiddenWorkspaceIds.has(edge.source) || hiddenWorkspaceIds.has(edge.target)) {
      continue;
    }
    const srcOk = nodeIdSet.has(edge.source);
    const tgtOk = nodeIdSet.has(edge.target);
    if (srcOk && tgtOk) {
      edges.push(edge);
    } else {
      orphanCount += 1;
    }
  }
  if (orphanCount > 0) {
    warnings.push(
      `Dropped ${orphanCount} edge(s) with missing source or target node id (not present after normalization).`,
    );
  }

  return {
    workId: payload.work_id == null ? "" : String(payload.work_id),
    nodes,
    edges,
    meta,
    nodeCount: nodes.length,
    edgeCount: edges.length,
    selectedNodeId: "",
    warnings,
  };
}

/**
 * @param {{ nodes: Array<{id: string}> }} graph
 * @param {string} preferredNodeId
 * @returns {string}
 */
export function resolveSelectedNodeId(graph, preferredNodeId = "") {
  const next = normalizeGraphNodeId(preferredNodeId);
  if (next && graph.nodes.some((node) => node.id === next)) {
    return next;
  }
  return graph.nodes[0]?.id || "";
}

/**
 * @param {{ edges: Array<{ id: string }> }} graph
 * @param {string} preferredEdgeId
 * @returns {string}
 */
export function resolveSelectedEdgeId(graph, preferredEdgeId = "") {
  const next = normalizeGraphEdgeId(preferredEdgeId);
  if (next && graph.edges.some((e) => e.id === next)) {
    return next;
  }
  return "";
}

/**
 * @param {{ nodes: Array<object>, edges: Array<object>, meta: object }} graph
 * @param {string} selectedNodeId
 * @param {string} [selectedEdgeId]
 * @returns {{ selectedNode: object | null, relatedEdges: Array<object>, selectedEdge: object | null }}
 */
export function deriveGraphDetail(graph, selectedNodeId, selectedEdgeId = "") {
  const eid = normalizeGraphEdgeId(selectedEdgeId);
  if (eid) {
    const selectedEdge = graph.edges.find((edge) => edge.id === eid) || null;
    if (selectedEdge) {
      return { selectedNode: null, relatedEdges: [], selectedEdge };
    }
  }
  const selectedNode = graph.nodes.find((node) => node.id === selectedNodeId) || null;
  const relatedEdges = selectedNode
    ? graph.edges.filter((edge) => edge.source === selectedNodeId || edge.target === selectedNodeId)
    : [];
  return { selectedNode, relatedEdges, selectedEdge: null };
}
