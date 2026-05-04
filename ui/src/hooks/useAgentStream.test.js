/** @vitest-environment jsdom */
import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

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
    const { result } = renderHook(() =>
      useAgentStream({
        onError,
        onFinalAnswer: vi.fn(),
        onEvent: vi.fn(),
      }),
    );
    await act(async () => {
      await result.current.stream({ question: "test" });
    });
    expect(onError).toHaveBeenCalledWith(expect.stringContaining("Network error"));
    expect(result.current.isStreaming).toBe(false);
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
    const onFinish = vi.fn();
    const { result } = renderHook(() =>
      useAgentStream({
        onError: vi.fn(),
        onFinalAnswer,
        onEvent,
        onFinish,
      }),
    );
    expect(result.current.isStreaming).toBe(false);
    await act(async () => {
      await result.current.stream({ question: "q" });
    });
    expect(onEvent).toHaveBeenCalled();
    expect(onFinalAnswer).toHaveBeenCalledWith(expect.objectContaining({ answer: "hi", type: "final_answer" }));
    expect(onFinish).toHaveBeenCalled();
    expect(result.current.isStreaming).toBe(false);
  });

  it("calls onError when SSE ends without final_answer", async () => {
    const enc = new TextEncoder();
    const sse = 'data: {"type":"intent_classified","answer_class":"inventory","source":"heuristic"}\n\n';
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
    const onError = vi.fn();
    const onFinalAnswer = vi.fn();
    const { result } = renderHook(() =>
      useAgentStream({
        onError,
        onFinalAnswer,
        onEvent: vi.fn(),
      }),
    );
    await act(async () => {
      await result.current.stream({ question: "q" });
    });
    expect(onFinalAnswer).not.toHaveBeenCalled();
    expect(onError).toHaveBeenCalledWith("Stream ended before a final answer was received.");
  });

  it("calls onError when non-SSE body is not valid JSON", async () => {
    globalThis.fetch.mockResolvedValueOnce({
      ok: true,
      headers: { get: () => "application/json" },
      text: async () => "not-json{",
    });
    const onError = vi.fn();
    const { result } = renderHook(() =>
      useAgentStream({
        onError,
        onFinalAnswer: vi.fn(),
        onEvent: vi.fn(),
      }),
    );
    await act(async () => {
      await result.current.stream({ question: "test" });
    });
    expect(onError).toHaveBeenCalledWith(expect.stringContaining("not valid JSON"));
  });

  it("returns silently on AbortError without abort intent (legacy)", async () => {
    const err = new Error("aborted");
    err.name = "AbortError";
    globalThis.fetch.mockRejectedValueOnce(err);
    const onError = vi.fn();
    const { result } = renderHook(() =>
      useAgentStream({
        onError,
        onFinalAnswer: vi.fn(),
        onEvent: vi.fn(),
      }),
    );
    await act(async () => {
      await result.current.stream({ question: "q" });
    });
    expect(onError).not.toHaveBeenCalled();
  });

  it("calls onAbort with user_cancel when abort() triggers AbortError", async () => {
    globalThis.fetch.mockImplementation((_url, opts) => {
      return new Promise((_resolve, reject) => {
        opts.signal.addEventListener("abort", () => {
          const e = new Error("aborted");
          e.name = "AbortError";
          reject(e);
        });
      });
    });
    const onAbort = vi.fn();
    const onError = vi.fn();
    const { result } = renderHook(() =>
      useAgentStream({
        onAbort,
        onError,
        onFinalAnswer: vi.fn(),
        onEvent: vi.fn(),
      }),
    );
    await act(async () => {
      const p = result.current.stream({ question: "q" });
      result.current.abort();
      await p;
    });
    expect(onAbort).toHaveBeenCalledWith({ reason: "user_cancel" });
    expect(onError).not.toHaveBeenCalled();
  });

  it("calls onAbort with replaced_by_new_request when a second stream aborts the first", async () => {
    let n = 0;
    globalThis.fetch.mockImplementation((_url, opts) => {
      n += 1;
      if (n === 1) {
        return new Promise((_resolve, reject) => {
          opts.signal.addEventListener("abort", () => {
            const e = new Error("aborted");
            e.name = "AbortError";
            reject(e);
          });
        });
      }
      return Promise.resolve({
        ok: true,
        headers: { get: () => "application/json" },
        text: async () =>
          '{"answer":"ok","citations":[],"tool_trace":[],"duration_ms":1,"run_metadata":{},"warnings":[]}',
      });
    });
    const onAbort = vi.fn();
    const onError = vi.fn();
    const { result } = renderHook(() =>
      useAgentStream({
        onAbort,
        onError,
        onFinalAnswer: vi.fn(),
        onEvent: vi.fn(),
      }),
    );
    await act(async () => {
      const p1 = result.current.stream({ question: "first" });
      await result.current.stream({ question: "second" });
      await p1;
    });
    expect(onAbort).toHaveBeenCalledWith({ reason: "replaced_by_new_request" });
    expect(onError).not.toHaveBeenCalled();
  });

  it("calls onFinish only once when first stream is superseded by second", async () => {
    let n = 0;
    globalThis.fetch.mockImplementation((_url, opts) => {
      n += 1;
      if (n === 1) {
        return new Promise((_resolve, reject) => {
          opts.signal.addEventListener("abort", () => {
            const e = new Error("aborted");
            e.name = "AbortError";
            reject(e);
          });
        });
      }
      return Promise.resolve({
        ok: true,
        headers: { get: () => "application/json" },
        text: async () =>
          '{"answer":"done","citations":[],"tool_trace":[],"duration_ms":1,"run_metadata":{},"warnings":[]}',
      });
    });
    const onFinish = vi.fn();
    const { result } = renderHook(() =>
      useAgentStream({
        onFinalAnswer: vi.fn(),
        onEvent: vi.fn(),
        onError: vi.fn(),
        onFinish,
      }),
    );
    await act(async () => {
      const p1 = result.current.stream({ question: "first" });
      await result.current.stream({ question: "second" });
      await p1;
    });
    expect(onFinish).toHaveBeenCalledTimes(1);
    expect(result.current.isStreaming).toBe(false);
  });

  it("keeps stream identity when callback props change", () => {
    const onErrorA = vi.fn();
    const onErrorB = vi.fn();
    const { result, rerender } = renderHook(
      ({ oe }) =>
        useAgentStream({
          onError: oe,
          onFinalAnswer: vi.fn(),
          onEvent: vi.fn(),
        }),
      { initialProps: { oe: onErrorA } },
    );
    const first = result.current.stream;
    rerender({ oe: onErrorB });
    expect(result.current.stream).toBe(first);
  });

  it("uses latest onError after rerender", async () => {
    const onError1 = vi.fn();
    const onError2 = vi.fn();
    const { result, rerender } = renderHook(
      ({ oe }) =>
        useAgentStream({
          onError: oe,
          onFinalAnswer: vi.fn(),
          onEvent: vi.fn(),
        }),
      { initialProps: { oe: onError1 } },
    );
    rerender({ oe: onError2 });
    globalThis.fetch.mockResolvedValueOnce({
      ok: false,
      status: 503,
      text: async () => "unavailable",
      headers: { get: () => "application/json" },
    });
    await act(async () => {
      await result.current.stream({ question: "q" });
    });
    expect(onError1).not.toHaveBeenCalled();
    expect(onError2).toHaveBeenCalledWith(expect.stringContaining("Agent error 503"));
  });

  it("calls onError for non-ok response", async () => {
    globalThis.fetch.mockResolvedValueOnce({
      ok: false,
      status: 503,
      text: async () => "agent_disabled",
      headers: { get: () => "application/json" },
    });
    const onError = vi.fn();
    const { result } = renderHook(() =>
      useAgentStream({
        onError,
        onFinalAnswer: vi.fn(),
        onEvent: vi.fn(),
      }),
    );
    await act(async () => {
      await result.current.stream({ question: "test" });
    });
    expect(onError).toHaveBeenCalledWith(expect.stringContaining("Agent error 503"));
  });
});
