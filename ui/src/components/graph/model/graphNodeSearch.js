/**
 * Local substring search over already-loaded graph nodes (no API).
 */

/**
 * @param {object} node
 * @returns {string} combined searchable text (not lowercased)
 */
export function nodeSearchHaystack(node) {
  const n = node && typeof node === "object" ? node : {};
  const parts = [n.displayLabel, n.label, n.id].filter((x) => x != null && String(x).trim());
  return parts.map((x) => String(x)).join("\u0000");
}

/**
 * @param {Array<{ id?: string, displayLabel?: string, label?: string }>} nodes
 * @param {string} query raw user input
 * @returns {Set<string>} node ids that match (empty Set when query is blank)
 */
export function filterNodeIdsBySearchSubstring(nodes, query) {
  const q = (query != null && String(query).trim().toLowerCase()) || "";
  if (!q) return new Set();
  const out = new Set();
  for (const n of nodes || []) {
    const id = n?.id != null ? String(n.id) : "";
    if (!id) continue;
    if (nodeSearchHaystack(n).toLowerCase().includes(q)) out.add(id);
  }
  return out;
}

/**
 * First matching node id in graph node order (stable for "focus first").
 *
 * @param {Array<{ id?: string, displayLabel?: string, label?: string }>} nodes
 * @param {Set<string>} matchIds
 * @returns {string}
 */
export function firstMatchingNodeIdInOrder(nodes, matchIds) {
  if (!(matchIds instanceof Set) || matchIds.size === 0) return "";
  for (const n of nodes || []) {
    const id = n?.id != null ? String(n.id) : "";
    if (id && matchIds.has(id)) return id;
  }
  return "";
}
