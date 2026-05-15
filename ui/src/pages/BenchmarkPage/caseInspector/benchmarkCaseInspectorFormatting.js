/**
 * Pure formatting helpers for benchmark case inspector (keeps JSX modules lean).
 */

/**
 * @param {Record<string, unknown>} issue
 * @param {(k: string, p?: Record<string, string>) => string} t
 */
export function formatInspectorIssueLine(issue, t) {
  const kind = String(issue.kind || "");
  if (kind === "failed_check" && Array.isArray(issue.checks)) {
    return t("benchmark.inspector.issue.failedChecks", { list: issue.checks.join(", ") });
  }
  if (kind === "case_status") {
    return t("benchmark.inspector.issue.caseStatus", {
      status: String(issue.status || ""),
      message: String(issue.message || "—"),
    });
  }
  if (kind === "metadata_mismatch") {
    return t("benchmark.inspector.issue.metadataMismatch", { field: String(issue.field || "") });
  }
  if (kind === "authorship_mismatch") {
    return t("benchmark.inspector.issue.authorshipMismatch", { pos: String(issue.position ?? "") });
  }
  if (kind === "reference_mismatch") {
    return t("benchmark.inspector.issue.referenceMismatch", { field: String(issue.field || "") });
  }
  if (kind === "layer2_missing_methods") {
    return t("benchmark.inspector.issue.layer2MissMethods", { count: String(issue.count ?? 0) });
  }
  if (kind === "layer2_extra_methods") {
    return t("benchmark.inspector.issue.layer2ExtraMethods", { count: String(issue.count ?? 0) });
  }
  if (kind === "layer2_missing_datasets") {
    return t("benchmark.inspector.issue.layer2MissDatasets", { count: String(issue.count ?? 0) });
  }
  if (kind === "layer2_extra_datasets") {
    return t("benchmark.inspector.issue.layer2ExtraDatasets", { count: String(issue.count ?? 0) });
  }
  if (kind === "diagnostics_hint") {
    return t("benchmark.inspector.issue.diagnosticsHint");
  }
  try {
    return JSON.stringify(issue);
  } catch {
    return kind || "issue";
  }
}

export function formatComparisonCellValue(value, fallback = null) {
  const resolved = value !== undefined ? value : fallback;
  return JSON.stringify(resolved);
}
