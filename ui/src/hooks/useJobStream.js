import { useEffect } from "react";

import { buildApiUrl } from "../services/apiClient.js";
import { ingestPhaseFromJob } from "../components/ingestion/ingestStripModel.js";
import { getIngestJob } from "../utils/workspaceStore.js";

/**
 * Merge a single stage_* SSE payload into a job snapshot (stages + job-level detail fields).
 * Exported for unit tests.
 *
 * @param {Record<string, unknown> | null | undefined} prevJob
 * @param {Record<string, unknown>} payload
 * @returns {Record<string, unknown>}
 */
export function mergeIngestJobStageEvent(prevJob, payload) {
  const base = prevJob && typeof prevJob === "object" ? prevJob : {};
  const currentStages = Array.isArray(base.stages) ? [...base.stages] : [];
  const idx = currentStages.findIndex((item) => String(item?.name || "") === String(payload.stage || ""));
  const prevRow = idx >= 0 ? currentStages[idx] : null;
  const prevM =
    prevRow?.metrics && typeof prevRow.metrics === "object" && !Array.isArray(prevRow.metrics)
      ? { ...prevRow.metrics }
      : {};
  const incM =
    payload.metrics && typeof payload.metrics === "object" && !Array.isArray(payload.metrics)
      ? payload.metrics
      : {};
  const mergedMetrics = { ...prevM, ...incM };
  const nextStage = {
    name: String(payload.stage || ""),
    status: String(payload.status || "running"),
    started_at: payload.started_at ?? prevRow?.started_at ?? null,
    finished_at: payload.finished_at !== undefined ? payload.finished_at : (prevRow?.finished_at ?? null),
    duration_ms: payload.duration_ms !== undefined ? payload.duration_ms : (prevRow?.duration_ms ?? null),
    expected_duration_ms: prevRow?.expected_duration_ms,
    metrics: mergedMetrics,
    error: payload.error !== undefined ? payload.error : (prevRow?.error ?? null),
  };
  const m = nextStage.metrics || {};
  if (m.detail_message != null && String(m.detail_message).trim()) {
    nextStage.detail_message = String(m.detail_message).trim().slice(0, 500);
  }
  if (m.subprogress_current != null && Number.isFinite(Number(m.subprogress_current))) {
    nextStage.subprogress_current = Number(m.subprogress_current);
  }
  if (m.subprogress_total != null && Number.isFinite(Number(m.subprogress_total))) {
    nextStage.subprogress_total = Number(m.subprogress_total);
  }
  if (idx >= 0) currentStages[idx] = { ...currentStages[idx], ...nextStage };
  else currentStages.push(nextStage);
  const merged = { ...base, stages: currentStages };
  const sid = String(payload.stage || "").trim();
  if (sid) {
    merged.active_stage = sid;
    merged.ingest_phase = ingestPhaseFromJob(merged, sid);
  }
  if (m.detail_message != null && String(m.detail_message).trim()) {
    merged.detail_message = String(m.detail_message).trim().slice(0, 500);
  }
  if (m.subprogress_current != null && Number.isFinite(Number(m.subprogress_current))) {
    merged.subprogress_current = Number(m.subprogress_current);
  }
  if (m.subprogress_total != null && Number.isFinite(Number(m.subprogress_total))) {
    merged.subprogress_total = Number(m.subprogress_total);
  }
  if (typeof payload.progress_pct === "number" && Number.isFinite(payload.progress_pct)) {
    merged.progress_pct = payload.progress_pct;
  }
  if (payload.ingest_phase != null && String(payload.ingest_phase).trim()) {
    merged.ingest_phase = String(payload.ingest_phase).trim();
  }
  if (payload.active_stage !== undefined) {
    merged.active_stage = String(payload.active_stage || "").trim();
  }
  if (payload.detail_message !== undefined) {
    merged.detail_message =
      payload.detail_message != null ? String(payload.detail_message).trim().slice(0, 500) : null;
  }
  if (payload.subprogress_current != null && Number.isFinite(Number(payload.subprogress_current))) {
    merged.subprogress_current = Number(payload.subprogress_current);
  }
  if (payload.subprogress_total != null && Number.isFinite(Number(payload.subprogress_total))) {
    merged.subprogress_total = Number(payload.subprogress_total);
  }
  if (Object.prototype.hasOwnProperty.call(payload, "progress_indeterminate")) {
    merged.progress_indeterminate = Boolean(payload.progress_indeterminate);
  }
  return merged;
}

export default function useJobStream({
  jobId,
  enabled,
  onUpdate,
  onTerminal,
  onError,
  fallbackPollMs = 2000,
}) {
  useEffect(() => {
    const id = String(jobId || "").trim();
    if (!enabled || !id) return undefined;
    let disposed = false;
    let failCount = 0;
    let source = null;
    let pollTimer = null;
    let currentJob = null;

    const stopPolling = () => {
      if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
      }
    };

    const runPollTick = async () => {
      try {
        const job = await getIngestJob(id);
        if (disposed) return;
        currentJob = job;
        onUpdate?.(job);
        if (job?.status === "completed" || job?.status === "failed") {
          stopPolling();
          onTerminal?.(job);
        }
      } catch (err) {
        if (disposed) return;
        failCount += 1;
        onError?.(err, failCount);
      }
    };

    const startPollingFallback = () => {
      if (pollTimer) return;
      stopEventSource();
      void runPollTick();
      pollTimer = setInterval(() => {
        void runPollTick();
      }, fallbackPollMs);
    };

    const stopEventSource = () => {
      if (source) {
        source.close();
        source = null;
      }
    };

    const url = buildApiUrl(`/v1/ingest/jobs/${encodeURIComponent(id)}/events`);
    source = new EventSource(url);

    source.addEventListener("snapshot", (evt) => {
      if (disposed) return;
      failCount = 0;
      try {
        const payload = JSON.parse(evt.data || "{}");
        currentJob = payload?.job || null;
        if (currentJob) onUpdate?.(currentJob);
      } catch {
        /* ignore malformed payload */
      }
    });

    const applyStage = (evt) => {
      if (disposed) return;
      failCount = 0;
      try {
        const payload = JSON.parse(evt.data || "{}");
        currentJob = mergeIngestJobStageEvent(currentJob, payload);
        onUpdate?.(currentJob);
      } catch {
        /* ignore malformed payload */
      }
    };
    source.addEventListener("stage_started", applyStage);
    source.addEventListener("stage_finished", applyStage);
    source.addEventListener("stage_failed", applyStage);
    source.addEventListener("stage_progress", applyStage);

    source.addEventListener("batch_progress", (evt) => {
      if (disposed) return;
      failCount = 0;
      try {
        const payload = JSON.parse(evt.data || "{}");
        currentJob = { ...(currentJob || {}), ...payload };
        onUpdate?.(currentJob);
      } catch {
        /* ignore malformed payload */
      }
    });

    source.addEventListener("terminal", (evt) => {
      if (disposed) return;
      try {
        const payload = JSON.parse(evt.data || "{}");
        currentJob = { ...(currentJob || {}), ...payload };
        onUpdate?.(currentJob);
        onTerminal?.(currentJob);
      } catch {
        onTerminal?.(currentJob);
      }
      stopEventSource();
      stopPolling();
    });

    source.onerror = (err) => {
      if (disposed) return;
      failCount += 1;
      onError?.(err, failCount);
      if (failCount >= 3 || source?.readyState === EventSource.CLOSED) {
        startPollingFallback();
      }
    };

    return () => {
      disposed = true;
      stopEventSource();
      stopPolling();
    };
  }, [enabled, jobId, onError, onTerminal, onUpdate, fallbackPollMs]);
}
