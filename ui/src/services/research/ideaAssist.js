import { apiClient, buildApiUrl } from "../apiClient.js";

export async function postIdeaAssist(body, config) {
  return apiClient.post(buildApiUrl("/v1/agent/idea-assist"), body, config);
}
