/**
 * Shared filtering/sorting for benchmark run case lists (Results dialog + Workbench).
 */

import { getRuntimeIntlLocale } from "../../i18n/runtimeIntlLocale.js";

export function collectFailedCheckNames(cases) {
  const names = new Set();
  for (const item of cases || []) {
    for (const c of item?.summary?.failed_checks || []) {
      if (c != null && String(c).trim()) names.add(String(c));
    }
  }
  return Array.from(names).sort((a, b) => a.localeCompare(b, getRuntimeIntlLocale(), { sensitivity: "base" }));
}

/**
 * @param {string} mode - 'all' | 'any' | 'checks'
 * @param {string[]} selectedChecks - used when mode === 'checks'
 */
export function filterCasesByFailure(cases, mode, selectedChecks) {
  const list = cases || [];
  if (mode === "all") return list;
  if (mode === "any") {
    return list.filter(
      (item) =>
        item.status === "failed" ||
        (Array.isArray(item?.summary?.failed_checks) && item.summary.failed_checks.length > 0),
    );
  }
  if (mode === "checks") {
    if (!selectedChecks?.length) return list;
    return list.filter((item) => {
      const fc = item?.summary?.failed_checks || [];
      return selectedChecks.some((name) => fc.includes(name));
    });
  }
  return list;
}

export function sortBenchmarkCases(cases, sortKey, dir) {
  const mult = dir === "desc" ? -1 : 1;
  const arr = [...(cases || [])];

  const val = (item) => {
    const summary = item?.summary || {};
    switch (sortKey) {
      case "status":
        return item.status || "";
      case "names_f1":
        return Number(summary.names_f1 ?? 0);
      case "sample_arxiv_f1":
        return Number(summary.sample_arxiv_f1 ?? 0);
      case "precision_methods":
        return Number(summary.precision_methods ?? 0);
      case "layer2_recall_ratio":
        return Number(summary.layer2_recall_ratio ?? 0);
      case "case_id":
      default:
        return item.case_id || "";
    }
  };

  arr.sort((a, b) => {
    const va = val(a);
    const vb = val(b);
    if (typeof va === "string" && typeof vb === "string") {
      return mult * va.localeCompare(vb, getRuntimeIntlLocale(), { sensitivity: "base" });
    }
    if (va < vb) return -1 * mult;
    if (va > vb) return 1 * mult;
    return 0;
  });
  return arr;
}

export const SORT_OPTIONS_LAYER1 = [
  { key: "case_id", label: "case_id (A–Z)" },
  { key: "status", label: "status" },
  { key: "names_f1", label: "names_f1" },
  { key: "sample_arxiv_f1", label: "sample_arxiv_f1" },
];

export const SORT_OPTIONS_LAYER2 = [
  { key: "case_id", label: "case_id (A–Z)" },
  { key: "status", label: "status" },
  { key: "precision_methods", label: "precision_methods" },
  { key: "layer2_recall_ratio", label: "layer2_recall_ratio" },
];

export function sortOptionsForFamily(family) {
  return family === "layer2" ? SORT_OPTIONS_LAYER2 : SORT_OPTIONS_LAYER1;
}
