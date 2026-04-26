import { beforeEach, describe, expect, it, vi } from "vitest";

const setStateMock = vi.fn();

vi.mock("react", () => ({
  useCallback: (fn) => fn,
  useRef: (value) => ({ current: value }),
  useState: (initial) => [initial, setStateMock],
}));

vi.mock("../services/apiClient.js", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    buildApiUrl: (path) => `http://localhost:8000${path}`,
  };
});

const { useAgentStream } = await import("./useAgentStream.js");

describe("useAgentStream", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    globalThis.fetch = vi.fn();
  });

  it("calls onError when fetch fails", async () => {
    globalThis.fetch.mockRejectedValueOnce(new Error("Network error"));
    const onError = vi.fn();
    const hook = useAgentStream({
      onError,
      onFinalAnswer: vi.fn(),
      onEvent: vi.fn(),
    });

    await hook.stream({ question: "test" });

    expect(onError).toHaveBeenCalledWith(expect.stringContaining("Network error"));
  });

  it("streams SSE frames and delivers final_answer", async () => {
    const enc = new TextEncoder();
    const sse =
      'data: {"type":"intent_classified","answer_class":"inventory","source":"heuristic"}\n\n' +
      'data: {"type":"final_answer","answer":"hi","citations":[],"tool_trace":[]}\n\n';
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(enc.encode(sse));
        controller.close();
      },
    });
    globalThis.fetch.mockResolvedValueOnce({
      ok: true,
      headers: { get: (h) => (String(h).toLowerCase() === "content-type" ? "text/event-stream" : null) },
      body: stream,
    });
    const onFinalAnswer = vi.fn();
    const onEvent = vi.fn();
    const hook = useAgentStream({
      onError: vi.fn(),
      onFinalAnswer,
      onEvent,
    });

    await hook.stream({ question: "q" });

    expect(onEvent).toHaveBeenCalled();
    expect(onFinalAnswer).toHaveBeenCalledWith(expect.objectContaining({ answer: "hi", type: "final_answer" }));
  });

  it("calls onError when non-SSE body is not valid JSON", async () => {
    globalThis.fetch.mockResolvedValueOnce({
      ok: true,
      headers: { get: () => "application/json" },
      text: async () => "not-json{",
    });
    const onError = vi.fn();
    const hook = useAgentStream({
      onError,
      onFinalAnswer: vi.fn(),
      onEvent: vi.fn(),
    });

    await hook.stream({ question: "test" });

    expect(onError).toHaveBeenCalledWith(expect.stringContaining("not valid JSON"));
  });

  it("returns silently on AbortError", async () => {
    const err = new Error("aborted");
    err.name = "AbortError";
    globalThis.fetch.mockRejectedValueOnce(err);
    const onError = vi.fn();
    const hook = useAgentStream({ onError, onFinalAnswer: vi.fn(), onEvent: vi.fn() });
    await hook.stream({ question: "q" });
    expect(onError).not.toHaveBeenCalled();
  });

  it("calls onError for non-ok response", async () => {
    globalThis.fetch.mockResolvedValueOnce({
      ok: false,
      status: 503,
      text: async () => "agent_disabled",
      headers: { get: () => "application/json" },
    });
    const onError = vi.fn();
    const hook = useAgentStream({
      onError,
      onFinalAnswer: vi.fn(),
      onEvent: vi.fn(),
    });

    await hook.stream({ question: "test" });

    expect(onError).toHaveBeenCalledWith(expect.stringContaining("Agent error 503"));
  });
});
