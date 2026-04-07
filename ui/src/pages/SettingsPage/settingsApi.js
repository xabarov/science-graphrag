import axios from "axios";

const api = axios.create({
  baseURL: "/v1",
});

function authHeaders() {
  const token =
    window.localStorage.getItem("access_token") || window.localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function getSettingsSchema() {
  const res = await api.get("/settings/schema", { headers: authHeaders() });
  return res.data;
}

export async function getSettingsSnapshot() {
  const res = await api.get("/settings", { headers: authHeaders() });
  return res.data;
}

export async function updateLlmSettings(payload) {
  const res = await api.patch("/settings/llm", payload, { headers: authHeaders() });
  return res.data;
}

export async function deleteLlmSecret() {
  const res = await api.delete("/settings/llm/secret", { headers: authHeaders() });
  return res.data;
}

export async function testLlmConnection(payload) {
  const res = await api.post("/settings/llm/test", payload, { headers: authHeaders() });
  return res.data;
}
