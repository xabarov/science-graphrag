/**
 * @param {string[]} prev
 * @param {string} caseId
 * @returns {string[]}
 */
export function toggleBenchmarkCaseSelection(prev, caseId) {
  if (prev.includes(caseId)) return prev.filter((x) => x !== caseId);
  return [...prev, caseId];
}
