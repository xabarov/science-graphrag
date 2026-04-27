/**
 * UI-only semantic projection: hide Neo4j authorship internals (Aggregator placeholders,
 * Authorship / AuthorshipReification) and present Work–Author links as AUTHORED edges.
 *
 * Mirrors backend intent of `collapse_authorship_for_reader_view` (works graph) for
 * workspace graphs that still carry aggregators until expand.
 */

/** Aggregator kinds that represent author/authorship neighborhoods on a Work. */
export const AUTHOR_AGGREGATOR_KINDS = new Set([
  "author_of_work",
  "authorship_of_work",
  "authorshipreification_of_work",
]);

/**
 * @param {unknown} node normalized graph node from {@link normalizeGraphPayload}
 * @returns {boolean}
 */
export function isAuthorAggregatorNode(node) {
  if (!node || typeof node !== "object") return false;
  const n = /** @type {Record<string, unknown>} */ (node);
  if (String(n.nodeKind || "") !== "Aggregator") return false;
  const raw = n.raw && typeof n.raw === "object" ? /** @type {Record<string, unknown>} */ (n.raw) : {};
  const hintsRaw = raw.aggregation_hints ?? raw.aggregationHints;
  const hints = hintsRaw && typeof hintsRaw === "object" && !Array.isArray(hintsRaw) ? hintsRaw : {};
  const kind = String(hints.aggregator_kind ?? hints.aggregatorKind ?? "")
    .trim()
    .toLowerCase();
  return AUTHOR_AGGREGATOR_KINDS.has(kind);
}

/**
 * @param {unknown} node normalized graph node
 * @returns {boolean}
 */
export function isAuthorshipLikeNode(node) {
  if (!node || typeof node !== "object") return false;
  const n = /** @type {Record<string, unknown>} */ (node);
  const t = String(n.type || "").trim();
  const k = String(n.nodeKind || "").trim();
  return t === "Authorship" || k === "Authorship" || k === "AuthorshipReification";
}

/**
 * @param {unknown} hints aggregation_hints object
 * @returns {string}
 */
function readExpandEndpoint(hints) {
  if (!hints || typeof hints !== "object" || Array.isArray(hints)) return "";
  const h = /** @type {Record<string, unknown>} */ (hints);
  return String(h.expand_endpoint ?? h.expandEndpoint ?? "").trim();
}

/**
 * Unique expand_endpoint values for author-related aggregators (for hidden prefetch).
 *
 * @param {{ nodes?: Array<object> }} graph normalized graph
 * @returns {string[]}
 */
export function collectAuthorAggregatorExpandEndpoints(graph) {
  const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
  const out = [];
  const seen = new Set();
  for (const n of nodes) {
    if (!isAuthorAggregatorNode(n)) continue;
    const raw = n.raw && typeof n.raw === "object" ? /** @type {Record<string, unknown>} */ (n.raw) : {};
    const hintsRaw = raw.aggregation_hints ?? raw.aggregationHints;
    const ep = readExpandEndpoint(
      hintsRaw && typeof hintsRaw === "object" && !Array.isArray(hintsRaw) ? hintsRaw : {},
    );
    if (!ep || seen.has(ep)) continue;
    seen.add(ep);
    out.push(ep);
  }
  return out;
}

/**
 * @param {string} workId
 * @param {string} authorId
 * @param {number} seq
 * @returns {string}
 */
function stableAuthoredEdgeId(workId, authorId, seq) {
  const payload = `${workId}\0AUTHORED\0${authorId}\0${seq}`;
  let h = 2166136261;
  for (let i = 0; i < payload.length; i++) {
    h ^= payload.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  const hex = (h >>> 0).toString(16).padStart(8, "0");
  return `e_ui_${hex}_${seq}`;
}

/**
 * @param {Record<string, unknown>} props
 * @returns {Record<string, unknown>}
 */
function pickAuthorshipEdgeProps(props) {
  if (!props || typeof props !== "object" || Array.isArray(props)) return {};
  const p = /** @type {Record<string, unknown>} */ (props);
  const out = {};
  for (const key of ["author_position", "is_corresponding", "raw_affiliation", "institution_name"]) {
    if (key in p && p[key] != null) out[key] = p[key];
  }
  return out;
}

/**
 * Returns a shallow-copied graph with author internals collapsed.
 *
 * @param {{
 *   nodes: Array<object>,
 *   edges: Array<object>,
 *   workId?: string,
 *   meta?: object,
 *   warnings?: string[],
 *   nodeCount?: number,
 *   edgeCount?: number,
 *   selectedNodeId?: string,
 * }} graph normalized graph from {@link normalizeGraphPayload}
 * @returns {typeof graph}
 */
export function projectAuthorSemanticGraph(graph) {
  if (!graph || typeof graph !== "object") return graph;
  const nodesIn = Array.isArray(graph.nodes) ? graph.nodes : [];
  const edgesIn = Array.isArray(graph.edges) ? graph.edges : [];
  const prevWarnings = Array.isArray(graph.warnings) ? graph.warnings : [];
  const warnings = prevWarnings.filter((w) => !String(w).includes("UI author semantic projection"));

  const authorAggIds = new Set();
  for (const n of nodesIn) {
    if (isAuthorAggregatorNode(n) && n && typeof n === "object" && "id" in n) {
      authorAggIds.add(String(/** @type {{ id: string }} */ (n).id));
    }
  }

  /** @type {Map<string, object>} */
  const nodeById = new Map();
  for (const n of nodesIn) {
    if (n && typeof n === "object" && n.id != null) nodeById.set(String(n.id), n);
  }

  const authorshipIds = new Set();
  for (const n of nodesIn) {
    if (isAuthorshipLikeNode(n) && n && typeof n === "object" && "id" in n) {
      authorshipIds.add(String(/** @type {{ id: string }} */ (n).id));
    }
  }

  /** @type {Map<string, string>} */
  const workByAsh = new Map();
  /** @type {Map<string, string>} */
  const authorByAsh = new Map();

  for (const e of edgesIn) {
    if (!e || typeof e !== "object") continue;
    const edge = /** @type {{ source: string, target: string, type?: string }} */ (e);
    const rt = String(edge.type || "").toUpperCase();
    const s = String(edge.source || "");
    const t = String(edge.target || "");
    if (rt === "HAS_AUTHORSHIP") {
      if (authorshipIds.has(t)) workByAsh.set(t, s);
      else if (authorshipIds.has(s)) workByAsh.set(s, t);
    } else if (rt === "OF_AUTHOR") {
      if (authorshipIds.has(s)) authorByAsh.set(s, t);
      else if (authorshipIds.has(t)) authorByAsh.set(t, s);
    }
  }

  /** @type {Set<string>} */
  const edgeIdsToDrop = new Set();
  for (const e of edgesIn) {
    if (!e || typeof e !== "object") continue;
    const edge = /** @type {{ id?: string, source: string, target: string, type?: string }} */ (e);
    const s = String(edge.source || "");
    const t = String(edge.target || "");
    const rt = String(edge.type || "").toUpperCase();
    if (authorAggIds.has(s) || authorAggIds.has(t)) {
      if (edge.id != null) edgeIdsToDrop.add(String(edge.id));
    }
    if (rt === "AGGREGATED" && (authorAggIds.has(s) || authorAggIds.has(t)) && edge.id != null) {
      edgeIdsToDrop.add(String(edge.id));
    }
    if (authorshipIds.has(s) || authorshipIds.has(t)) {
      if (edge.id != null) edgeIdsToDrop.add(String(edge.id));
    }
  }

  /**
   * @param {{
   *   id: string,
   *   source: string,
   *   target: string,
   *   type: string,
   *   displayType: string,
   *   sourceLabel: string,
   *   targetLabel: string,
   *   summary?: string,
   *   direction?: string,
   *   rawExtra?: Record<string, unknown>,
   * }} p
   */
  function makeNormalizedEdge(p) {
    const raw = {
      id: p.id,
      source: p.source,
      target: p.target,
      type: p.type,
      display_type: p.displayType,
      source_label: p.sourceLabel,
      target_label: p.targetLabel,
      summary: p.summary ?? "",
      direction: p.direction ?? "outgoing",
      ...(p.rawExtra || {}),
    };
    return {
      id: p.id,
      source: p.source,
      target: p.target,
      type: p.type,
      displayType: p.displayType,
      sourceLabel: p.sourceLabel,
      targetLabel: p.targetLabel,
      summary: p.summary ?? "",
      direction: p.direction ?? "outgoing",
      raw,
    };
  }

  /** @type {Array<object>} */
  const virtualEdges = [];
  let seq = 0;
  for (const [ashId, workId] of workByAsh.entries()) {
    const authorId = authorByAsh.get(ashId);
    if (!workId || !authorId) continue;
    const ashNode = nodeById.get(ashId);
    const props =
      ashNode && typeof ashNode === "object" && "properties" in ashNode
        ? pickAuthorshipEdgeProps(/** @type {{ properties?: Record<string, unknown> }} */ (ashNode).properties)
        : {};
    const workNode = nodeById.get(workId);
    const authorNode = nodeById.get(authorId);
    const wl =
      workNode && typeof workNode === "object"
        ? String(
            (/** @type {{ displayLabel?: string, label?: string }} */ (workNode).displayLabel || "").trim() ||
              (/** @type {{ label?: string }} */ (workNode).label || ""),
          )
        : "";
    const al =
      authorNode && typeof authorNode === "object"
        ? String(
            (/** @type {{ displayLabel?: string, label?: string }} */ (authorNode).displayLabel || "").trim() ||
              (/** @type {{ label?: string }} */ (authorNode).label || ""),
          )
        : "";
    const eid = stableAuthoredEdgeId(workId, authorId, seq);
    seq += 1;
    virtualEdges.push(
      makeNormalizedEdge({
        id: eid,
        source: workId,
        target: authorId,
        type: "AUTHORED",
        displayType: "wrote",
        sourceLabel: wl,
        targetLabel: al,
        rawExtra: { properties: props, via: ["HAS_AUTHORSHIP", "OF_AUTHOR"] },
      }),
    );
  }

  /** @type {Array<object>} */
  const institutionBridgeEdges = [];
  let instSeq = 0;
  for (const e of edgesIn) {
    if (!e || typeof e !== "object") continue;
    const edge = /** @type {{ source: string, target: string, type?: string }} */ (e);
    const rt = String(edge.type || "").toUpperCase();
    if (rt !== "AFFILIATED_WITH") continue;
    const s = String(edge.source || "");
    const t = String(edge.target || "");
    let ashId = "";
    let instId = "";
    if (authorshipIds.has(s) && !authorshipIds.has(t)) {
      ashId = s;
      instId = t;
    } else if (authorshipIds.has(t) && !authorshipIds.has(s)) {
      ashId = t;
      instId = s;
    } else {
      continue;
    }
    const authorId = authorByAsh.get(ashId);
    if (!authorId || !instId) continue;
    const instNode = nodeById.get(instId);
    const isInst =
      instNode &&
      typeof instNode === "object" &&
      (String(/** @type {{ type?: string }} */ (instNode).type || "") === "Institution" ||
        String(/** @type {{ nodeKind?: string }} */ (instNode).nodeKind || "") === "Institution");
    if (!isInst) continue;
    const eid = stableAuthoredEdgeId(authorId, instId, 5000 + instSeq);
    instSeq += 1;
    const authorNode = nodeById.get(authorId);
    const instLabel =
      instNode && typeof instNode === "object"
        ? String(
            (/** @type {{ displayLabel?: string, label?: string }} */ (instNode).displayLabel || "").trim() ||
              (/** @type {{ label?: string }} */ (instNode).label || ""),
          )
        : "";
    const al =
      authorNode && typeof authorNode === "object"
        ? String(
            (/** @type {{ displayLabel?: string, label?: string }} */ (authorNode).displayLabel || "").trim() ||
              (/** @type {{ label?: string }} */ (authorNode).label || ""),
          )
        : "";
    institutionBridgeEdges.push(
      makeNormalizedEdge({
        id: eid,
        source: authorId,
        target: instId,
        type: "AFFILIATED_WITH",
        displayType: "affiliated with",
        sourceLabel: al,
        targetLabel: instLabel,
        rawExtra: { via: ["Authorship", "AFFILIATED_WITH"] },
      }),
    );
  }

  const keptNodes = nodesIn.filter((n) => {
    if (!n || typeof n !== "object" || n.id == null) return false;
    const id = String(n.id);
    if (authorAggIds.has(id)) return false;
    if (authorshipIds.has(id)) return false;
    return true;
  });

  const keptEdges = edgesIn.filter((e) => {
    if (!e || typeof e !== "object") return false;
    const eid = e.id != null ? String(e.id) : "";
    if (!eid) return true;
    return !edgeIdsToDrop.has(eid);
  });

  const existingKeys = new Set(
    keptEdges.map((e) => {
      if (!e || typeof e !== "object") return "";
      return `${String(e.source)}|${String(e.type || "").toUpperCase()}|${String(e.target)}`;
    }),
  );

  /** @param {object} ve */
  function ingestVirtual(ve) {
    const typ = String(ve.type || "").toUpperCase();
    const key = `${ve.source}|${typ}|${ve.target}`;
    if (existingKeys.has(key)) return;
    existingKeys.add(key);
    keptEdges.push(ve);
  }

  for (const ve of virtualEdges) ingestVirtual(ve);
  for (const ve of institutionBridgeEdges) ingestVirtual(ve);

  if (authorAggIds.size > 0 || authorshipIds.size > 0) {
    warnings.push(
      "UI author semantic projection: collapsed authorship internals (Aggregator / Authorship) into Work–Author view.",
    );
  }

  return {
    ...graph,
    nodes: keptNodes,
    edges: keptEdges,
    nodeCount: keptNodes.length,
    edgeCount: keptEdges.length,
    warnings,
  };
}
