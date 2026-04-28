/**
 * Prefer requested neighbor cap for subtitle; fall back to applied cap (work graph).
 *
 * @param {Record<string, unknown>} meta
 * @returns {string | null} numeric string or null if neither is usable
 */
function neighborLimitLabel(meta) {
  const req = meta.neighbor_limit;
  const applied = meta.neighbor_limit_applied;
  if (typeof req === "number" && Number.isFinite(req)) return String(req);
  if (typeof applied === "number" && Number.isFinite(applied)) return String(applied);
  if (req != null && req !== "") return String(req);
  if (applied != null && applied !== "") return String(applied);
  return null;
}

/**
 * One-line graph mode description from API ``meta`` (Phase 0 contract).
 *
 * @param {Record<string, unknown> | null | undefined} meta
 * @param {(key: string, params?: Record<string, string>) => string} t
 * @returns {string | null}
 */
export function graphContractSubtitle(meta, t) {
  if (!meta || typeof meta.graph_contract_version !== "number") return null;
  const mode = String(meta.graph_mode || "");
  const lim = neighborLimitLabel(meta) || "";
  if (mode === "work_capped") {
    return t("graph.contractSubtitle.workCapped", { limit: lim || "—" });
  }
  if (mode === "work_workspace_context") {
    return t("graph.contractSubtitle.workWorkspaceContext", { limit: lim || "—" });
  }
  if (mode === "workspace_union") {
    return t("graph.contractSubtitle.workspaceUnion");
  }
  if (mode === "workspace_v2") {
    const m = String(meta.mode || "inner_only");
    return t("graph.contractSubtitle.workspaceV2", { mode: m });
  }
  if (mode === "workspace_neighbors") {
    return t("graph.contractSubtitle.workspaceNeighbors");
  }
  if (mode === "work_expand_aggregator") {
    return t("graph.contractSubtitle.expandWork");
  }
  if (mode === "workspace_expand_aggregator") {
    return t("graph.contractSubtitle.expandWorkspace");
  }
  return null;
}
