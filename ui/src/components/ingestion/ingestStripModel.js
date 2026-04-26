/**
 * Pure helpers for compact ingest strip (product phase + active stage id).
 */

/** @type {Record<string, string>} */
const STAGE_TO_PHASE = {
  parse_pdf: "preparing_document",
  extract_meta: "preparing_document",
  enrich_openalex: "building_graph",
  enrich_ror: "building_graph",
  write_graph: "building_graph",
  resolve_references: "building_graph",
  chunk: "preparing_search",
  extract_claims: "preparing_search",
  embed: "preparing_search",
  attach_workspace: "finalizing",
};

/**
 * @param {unknown} stageRow
 * @returns {string}
 */
export function ingestStageIdFromRow(stageRow) {
  if (!stageRow || typeof stageRow !== "object") return "";
  const s = stageRow.stage != null ? String(stageRow.stage) : "";
  if (s) return s;
  return stageRow.name != null ? String(stageRow.name) : "";
}

/**
 * @param {unknown[]} stages
 * @returns {Record<string, unknown> | null}
 */
export function pickActiveIngestStage(stages) {
  if (!Array.isArray(stages) || stages.length === 0) return null;
  const running = stages.find((s) => String(s?.status || "").toLowerCase() === "running");
  if (running) return running;
  for (let i = stages.length - 1; i >= 0; i -= 1) {
    const st = stages[i];
    const status = String(st?.status || "").toLowerCase();
    if (status === "failed") return st;
  }
  return stages[stages.length - 1] || null;
}

/**
 * @param {string} stageId
 * @returns {string}
 */
export function ingestProductPhaseKey(stageId) {
  const sid = String(stageId || "").trim();
  if (!sid) return "preparing_document";
  return STAGE_TO_PHASE[sid] || "preparing_document";
}
