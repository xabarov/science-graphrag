/** @vitest-environment jsdom */
import { renderHook, act } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

let lastStreamPayload = null;
/** @type {"minimal" | "many_events"} */
let streamScenario = "minimal";

vi.mock("../../../../hooks/useAgentStream.js", () => ({
  useAgentStream: vi.fn((opts) => ({
    stream: vi.fn(async (payload) => {
      lastStreamPayload = payload;
      if (streamScenario === "many_events") {
        for (let i = 0; i < 100; i += 1) {
          opts.onEvent({ type: "intent_classified", answer_class: "x", source: "h", seq: i });
        }
      }
      opts.onFinalAnswer({
        answer: "ok",
        citations: [],
        tool_trace: [],
        thread_id: payload.threadId,
        session_summary_excerpt: "Q: test\nA: ok",
        run_metadata: { compaction: { kinds: ["turn_digest"] } },
        warnings: [],
      });
    }),
    isStreaming: false,
    abort: vi.fn(),
  })),
}));

describe("useAskSubmit", () => {
  beforeEach(() => {
    streamScenario = "minimal";
    lastStreamPayload = null;
  });

  it("passes threadId and historyDigest to streamAgent", async () => {
    const { useAskSubmit } = await import("./useAskSubmit.js");
    const { useAgentStream } = await import("../../../../hooks/useAgentStream.js");

    const onResult = vi.fn();
    const { result } = renderHook(() =>
      useAskSubmit({
        workspaceId: "ws-1",
        onResult,
        useStreamingAgent: true,
      }),
    );

    await act(async () => {
      await result.current.submit({
        query: "hello",
        threadId: "sess-1",
        historyDigest: [{ user: "u", assistant: "a" }],
      });
    });

    expect(useAgentStream).toHaveBeenCalled();
    expect(lastStreamPayload).toMatchObject({
      question: "hello",
      threadId: "sess-1",
      historyDigest: [{ user: "u", assistant: "a" }],
    });
    expect(onResult).toHaveBeenCalled();
    const norm = onResult.mock.calls[0][0];
    expect(norm.session_summary_excerpt).toContain("Q: test");
    expect(norm.run_metadata?.compaction?.kinds).toContain("turn_digest");
  });

  it("passes userStructuredAnswer to streamAgent", async () => {
    const { useAskSubmit } = await import("./useAskSubmit.js");
    const { result } = renderHook(() =>
      useAskSubmit({
        workspaceId: "ws-1",
        onResult: vi.fn(),
        useStreamingAgent: true,
      }),
    );

    await act(async () => {
      await result.current.submit({
        query: "(continue)",
        threadId: "sess-1",
        historyDigest: null,
        userStructuredAnswer: { request_id: "r1", answers: [{ question_id: "q1", selected_option_ids: ["a"] }] },
      });
    });

    expect(lastStreamPayload).toMatchObject({
      question: "(continue)",
      userStructuredAnswer: { request_id: "r1", answers: [{ question_id: "q1", selected_option_ids: ["a"] }] },
    });
  });

  it("exposes abort with submit hook", async () => {
    const { useAskSubmit } = await import("./useAskSubmit.js");
    const { result } = renderHook(() =>
      useAskSubmit({
        workspaceId: "ws-1",
        onResult: vi.fn(),
        useStreamingAgent: true,
      }),
    );
    expect(typeof result.current.abort).toBe("function");
  });

  it("caps captured stream events at 80", async () => {
    streamScenario = "many_events";
    const { useAskSubmit } = await import("./useAskSubmit.js");
    const { result } = renderHook(() =>
      useAskSubmit({
        workspaceId: "ws-1",
        onResult: vi.fn(),
        useStreamingAgent: true,
      }),
    );

    let pack = null;
    await act(async () => {
      pack = await result.current.submit({ query: "q" });
    });

    expect(pack?.streamEvents?.length).toBe(80);
  });
});
