import { apiClient, buildApiUrl } from "../apiClient.js";

export async function postAgentQuery(body, config) {
  return apiClient.post(buildApiUrl("/v1/agent/query"), body, config);
}

export async function postAgentQueryV2(body, config) {
  return apiClient.post(buildApiUrl("/v2/agent/query"), body, {
    ...config,
    headers: {
      ...config?.headers,
      Accept: "application/json",
    },
  });
}
