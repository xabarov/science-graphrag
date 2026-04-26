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

  it("returns silently on AbortError", async () => {
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
