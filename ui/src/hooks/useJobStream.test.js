import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const getIngestJobMock = vi.fn();
let lastCleanup = null;

vi.mock("../utils/workspaceStore.js", () => ({
  getIngestJob: (...args) => getIngestJobMock(...args),
}));

vi.mock("react", () => ({
  useEffect: (fn) => {
    lastCleanup = fn();
  },
}));

const { default: useJobStream, mergeIngestJobStageEvent } = await import("./useJobStream.js");

class FakeEventSource {
  static instances = [];
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSED = 2;

  constructor(url) {
    this.url = url;
    this.readyState = FakeEventSource.OPEN;
    this.onerror = null;
    this.listeners = new Map();
    FakeEventSource.instances.push(this);
  }

  addEventListener(type, listener) {
    const arr = this.listeners.get(type) || [];
    arr.push(listener);
    this.listeners.set(type, arr);
  }

  emit(type, payload) {
    const listeners = this.listeners.get(type) || [];
    for (const listener of listeners) listener({ data: JSON.stringify(payload) });
  }

  fail(err = new Error("stream_error")) {
    if (typeof this.onerror === "function") this.onerror(err);
  }

  close() {
    this.readyState = FakeEventSource.CLOSED;
  }
}

describe("useJobStream", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    getIngestJobMock.mockReset();
    FakeEventSource.instances = [];
    globalThis.EventSource = FakeEventSource;
    lastCleanup = null;
  });

  afterEach(() => {
    if (typeof lastCleanup === "function") lastCleanup();
    vi.useRealTimers();
  });

  it("merges stage events and handles terminal", () => {
    const onUpdate = vi.fn();
    const onTerminal = vi.fn();
    useJobStream({
      jobId: "job-1",
      enabled: true,
      onUpdate,
      onTerminal,
      onError: vi.fn(),
      fallbackPollMs: 2000,
    });

    const source = FakeEventSource.instances[0];
    source.emit("snapshot", { job: { job_id: "job-1", status: "running", stages: [] } });
    source.emit("stage_started", { job_id: "job-1", stage: "parse_pdf", status: "running" });
    source.emit("stage_finished", { job_id: "job-1", stage: "parse_pdf", status: "completed" });
    source.emit("terminal", { job_id: "job-1", status: "completed" });

    expect(onUpdate).toHaveBeenCalled();
    const lastArg = onUpdate.mock.calls[onUpdate.mock.calls.length - 1][0];
    expect(lastArg.stages[0].name).toBe("parse_pdf");
    expect(lastArg.stages[0].status).toBe("completed");
    expect(onTerminal).toHaveBeenCalledTimes(1);
  });

  it("falls back to polling after three stream errors", async () => {
    getIngestJobMock.mockResolvedValueOnce({ job_id: "job-2", status: "running", stages: [] });
    getIngestJobMock.mockResolvedValueOnce({ job_id: "job-2", status: "failed", stages: [] });
    const onError = vi.fn();
    const onTerminal = vi.fn();

    useJobStream({
      jobId: "job-2",
      enabled: true,
      onUpdate: vi.fn(),
      onTerminal,
      onError,
      fallbackPollMs: 2000,
    });
    const source = FakeEventSource.instances[0];
    source.fail();
    source.fail();
    source.fail();

    vi.advanceTimersByTime(1);
    await Promise.resolve();
    vi.advanceTimersByTime(2000);
    await Promise.resolve();

    expect(onError).toHaveBeenCalledTimes(3);
    expect(getIngestJobMock).toHaveBeenCalled();
    expect(onTerminal).toHaveBeenCalledTimes(1);
  });
});

describe("mergeIngestJobStageEvent", () => {
  it("merges metrics shallowly so empty payload does not wipe snapshot metrics", () => {
    const prev = {
      job_id: "j1",
      stages: [{ name: "parse_pdf", status: "running", metrics: { vl_pages_total: 10, vl_pages_done: 3 } }],
    };
    const out = mergeIngestJobStageEvent(prev, { stage: "parse_pdf", status: "running", metrics: {} });
    expect(out.stages[0].metrics).toEqual({ vl_pages_total: 10, vl_pages_done: 3 });
  });

  it("overlays new metric keys onto previous", () => {
    const prev = {
      stages: [{ name: "embed", status: "running", metrics: { chunks_total: 5 } }],
    };
    const out = mergeIngestJobStageEvent(prev, {
      stage: "embed",
      status: "running",
      metrics: { chunks_done: 2 },
    });
    expect(out.stages[0].metrics).toEqual({ chunks_total: 5, chunks_done: 2 });
  });

  it("keeps server ingest_phase when present on job", () => {
    const prev = {
      ingest_phase: "building_graph",
      stages: [{ name: "parse_pdf", status: "running", metrics: {} }],
    };
    const out = mergeIngestJobStageEvent(prev, { stage: "parse_pdf", status: "running", metrics: {} });
    expect(out.ingest_phase).toBe("building_graph");
  });

  it("preserves stage finished_at when progress event omits it", () => {
    const prev = {
      stages: [{ name: "chunk", status: "completed", finished_at: "2026-01-01T00:00:00Z" }],
    };
    const out = mergeIngestJobStageEvent(prev, {
      stage: "chunk",
      status: "running",
      metrics: { detail_message: "re-run" },
    });
    expect(out.stages[0].finished_at).toBe("2026-01-01T00:00:00Z");
  });

  it("merges top-level canonical fields from stage_progress payload", () => {
    const prev = { job_id: "j1", stages: [{ name: "embed", status: "running", metrics: {} }] };
    const out = mergeIngestJobStageEvent(prev, {
      stage: "embed",
      status: "running",
      metrics: { detail_message: "chunk 2/5" },
      progress_pct: 0.42,
      ingest_phase: "preparing_search",
      active_stage: "embed",
      detail_message: "chunk 2/5",
      subprogress_current: 2,
      subprogress_total: 5,
      progress_indeterminate: false,
    });
    expect(out.progress_pct).toBe(0.42);
    expect(out.ingest_phase).toBe("preparing_search");
    expect(out.active_stage).toBe("embed");
    expect(out.detail_message).toBe("chunk 2/5");
    expect(out.subprogress_current).toBe(2);
    expect(out.subprogress_total).toBe(5);
    expect(out.progress_indeterminate).toBe(false);
  });

  it("merges progress_pct zero from SSE payload", () => {
    const prev = { job_id: "j1", progress_pct: 0.5, stages: [] };
    const out = mergeIngestJobStageEvent(prev, {
      stage: "parse_pdf",
      status: "running",
      metrics: {},
      progress_pct: 0,
    });
    expect(out.progress_pct).toBe(0);
  });

  it("clears progress_indeterminate when SSE sends false", () => {
    const prev = { job_id: "j1", progress_indeterminate: true, stages: [] };
    const out = mergeIngestJobStageEvent(prev, {
      stage: "parse_pdf",
      status: "running",
      metrics: {},
      progress_indeterminate: false,
    });
    expect(out.progress_indeterminate).toBe(false);
  });
});
