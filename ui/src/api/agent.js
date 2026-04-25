import { postAgentQuery } from "../services/researchApi.js";

export async function runAgentQuery(payload, config) {
  return postAgentQuery(payload, config);
}
