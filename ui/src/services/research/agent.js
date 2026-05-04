import { apiClient, buildApiUrl } from "../apiClient.js";

export async function postAgentQueryV2(body, config) {
  return apiClient.post(buildApiUrl("/v2/agent/query"), body, {
    ...config,
    headers: {
      ...config?.headers,
      Accept: "application/json",
    },
  });
}
