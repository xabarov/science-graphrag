import axios from "axios";

const api = axios.create({
  baseURL: "/v1",
});

function authHeaders() {
  // Backend currently doesn't require auth for benchmark endpoints,
  // but this keeps the UI consistent with other dashboards.
  const token =
    window.localStorage.getItem("access_token") || window.localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function listBenchmarkCases({ family = "layer1", tier, q, limit = 200, offset = 0 } = {}) {
  const res = await api.get("/benchmark/cases", {
    params: { family, tier, q, limit, offset },
    headers: authHeaders(),
  });
  return res.data;
}

export async function getBenchmarkCaseDetail(caseId, { family = "layer1" } = {}) {
  const res = await api.get(`/benchmark/cases/${encodeURIComponent(caseId)}`, {
    params: { family },
    headers: authHeaders(),
  });
  return res.data;
}

export async function runBenchmark({ case_ids, label, family = "layer1" } = {}) {
  const res = await api.post(
    "/benchmark/runs",
    { case_ids, label, family },
    {
      headers: authHeaders(),
    },
  );
  return res.data;
}

export async function listBenchmarkRuns() {
  const res = await api.get("/benchmark/runs", { headers: authHeaders() });
  return res.data;
}

export async function getBenchmarkRun(runId) {
  const res = await api.get(`/benchmark/runs/${encodeURIComponent(runId)}`, {
    headers: authHeaders(),
  });
  return res.data;
}

export async function deleteBenchmarkRun(runId) {
  const res = await api.delete(`/benchmark/runs/${encodeURIComponent(runId)}`, {
    headers: authHeaders(),
  });
  return res.data;
}

export async function pollProgress(runId, { intervalMs = 2000, maxWaitMs = 30 * 60 * 1000 } = {}) {
  const startedAt = Date.now();

  // Poll until run reaches a terminal status.
  // Backend statuses: queued/running/completed/failed/cancelled.
  while (Date.now() - startedAt < maxWaitMs) {
    const run = await getBenchmarkRun(runId);
    const payload = run?.data || run;
    const status = payload?.status;

    if (["completed", "failed", "cancelled"].includes(status)) {
      return payload;
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }

  throw new Error("poll_progress_timeout");
}

