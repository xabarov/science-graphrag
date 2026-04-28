import { getWorkGraph } from "../../../services/researchApi.js";
import { normalizeGraphPayload } from "./graphViewState.js";

/**
 * Fetches `/v1/works/{work_id}/graph` and normalizes payload for graph UI (single adapter entry).
 * @param {string} workId
 * @param {{ depth?: number, neighborLimit?: number }} [options]
 * @returns {Promise<ReturnType<typeof normalizeGraphPayload>>}
 */
export async function fetchWorkGraphNormalized(workId, options = {}) {
  const res = await getWorkGraph(workId, options);
  return normalizeGraphPayload(res.data);
}
