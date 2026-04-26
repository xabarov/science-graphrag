import { defaultCaseDetailFamily } from "./default.js";
import { graphCaseDetailFamily } from "./graph.js";
import { layer1CaseDetailFamily } from "./layer1.js";

/** @type {Record<string, import("./caseDetailFamilyTypes.js").CaseDetailFamilyConfig>} */
const BY_FAMILY_ID = {
  layer1: { ...defaultCaseDetailFamily, ...layer1CaseDetailFamily },
  graph: { ...defaultCaseDetailFamily, ...graphCaseDetailFamily },
};

/**
 * Resolve CaseDetailDialog behavior for a benchmark family id.
 * Add new families by creating `families/<name>.js` and a line in BY_FAMILY_ID.
 * @param {string} [family]
 * @returns {import("./caseDetailFamilyTypes.js").CaseDetailFamilyConfig}
 */
export function getCaseDetailFamilyConfig(family) {
  if (!family) return { ...defaultCaseDetailFamily };
  const specific = BY_FAMILY_ID[family];
  return specific ? { ...specific } : { ...defaultCaseDetailFamily };
}
