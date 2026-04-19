/**
 * Semantic + structural community ids for scholarly graphs (science-graphrag).
 * Unions nodes linked by authorship-related edge types so force clustering matches domain structure.
 *
 * @param {Array<{ id: string }>} nodes
 * @param {Array<{ source: string, target: string, type?: string }>} links
 * @returns {Map<string, string>} nodeId -> communityId
 */
export function detectScienceHybridCommunities(nodes, links) {
  if (nodes.length === 0) return new Map();

  const ids = new Set(nodes.map((n) => n.id));
  const parent = new Map();
  nodes.forEach((n) => parent.set(n.id, n.id));

  function find(x) {
    let p = parent.get(x);
    if (p !== x) {
      p = find(p);
      parent.set(x, p);
    }
    return p;
  }

  function union(a, b) {
    const ra = find(a);
    const rb = find(b);
    if (ra === rb) return;
    if (String(ra) < String(rb)) {
      parent.set(rb, ra);
    } else {
      parent.set(ra, rb);
    }
  }

  /** Neo4j-style relationship types that tie Work ↔ Authorship ↔ Author subgraphs. */
  const SEMANTIC_EDGE_TYPES = new Set(["HAS_AUTHORSHIP", "OF_AUTHOR"]);

  links.forEach((l) => {
    const t = l.type == null ? "" : String(l.type);
    if (!SEMANTIC_EDGE_TYPES.has(t)) return;
    if (!ids.has(l.source) || !ids.has(l.target)) return;
    union(l.source, l.target);
  });

  const communities = new Map();
  nodes.forEach((n) => {
    const root = find(n.id);
    communities.set(n.id, `sem:${root}`);
  });
  return communities;
}
