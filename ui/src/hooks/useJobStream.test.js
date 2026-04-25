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

const { default: useJobStream } = await import("./useJobStream.js");

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
