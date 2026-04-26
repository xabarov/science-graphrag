/** Max rows rendered per compare delta table (performance). */
export const BENCHMARK_COMPARE_TABLE_CAP = 200;

/**
 * @param {unknown} rows
 * @param {string} caseQ
 * @param {string} metricQ
 * @returns {Array<Record<string, unknown>>}
 */
export function filterBenchmarkCompareDeltaRows(rows, caseQ, metricQ) {
  if (!rows?.length) return [];
  const cq = (caseQ || "").trim().toLowerCase();
  const mq = (metricQ || "").trim().toLowerCase();
  return rows.filter((r) => {
    if (cq && !String(r.case_id).toLowerCase().includes(cq)) return false;
    if (mq && !String(r.metric).toLowerCase().includes(mq)) return false;
    return true;
  });
}

/**
 * @param {string} filename
 * @param {string} text
 * @param {string} [mime]
 */
export function downloadBenchmarkCompareText(filename, text, mime) {
  const blob = new Blob([text], { type: mime || "application/octet-stream" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
