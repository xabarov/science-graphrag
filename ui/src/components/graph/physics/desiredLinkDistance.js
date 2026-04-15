/**
 * Target edge length for force simulation (science-graph relationship types).
 */

const DEFAULT_DISTANCE = 180;

/** @type {Record<string, number>} */
const BY_EDGE_TYPE = {
  CITES: 200,
  USES_METHOD: 170,
  EVALUATED_ON: 170,
  HAS_AUTHORSHIP: 160,
  AUTHORED_BY: 160,
  AFFILIATED_WITH: 190,
  APPEARS_IN: 200,
  MENTIONS: 190,
  RELATED_TO: 175,
};

/**
 * @param {unknown} edgeType
 * @returns {number}
 */
export function getScienceDesiredDistance(edgeType) {
  const key = edgeType == null ? "" : String(edgeType).trim();
  if (key && BY_EDGE_TYPE[key] != null) return BY_EDGE_TYPE[key];
  return DEFAULT_DISTANCE;
}
