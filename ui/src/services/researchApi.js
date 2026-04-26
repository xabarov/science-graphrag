/** Barrel: public research API surface (split under `./research/`). */
export { formatResearchApiError } from "./research/errors.js";
export { getResearchApiBaseUrl, getHealth } from "./research/meta.js";
export {
  formatRetrievalSummaryLines,
  buildAskAnswerRationale,
  normalizeQueryResponse,
} from "./research/queryModel.js";
export { buildQueryBody, postQuery } from "./research/queryHttp.js";
export {
  listAskSessions,
  createAskSession,
  patchAskSession,
  deleteAskSession,
} from "./research/askSessions.js";
export { postAgentQuery, postAgentQueryV2 } from "./research/agent.js";
export { postIdeaAssist } from "./research/ideaAssist.js";
export {
  getWorks,
  workPdfUrl,
  getWorkSources,
  getWorkDetail,
  getWorkChunks,
  getWorkExtractedBody,
  getWorkClaims,
} from "./research/works.js";
export { getWorkGraph, expandAggregator } from "./research/graph.js";
