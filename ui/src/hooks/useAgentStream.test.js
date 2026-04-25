import { beforeEach, describe, expect, it, vi } from "vitest";

const setStateMock = vi.fn();

vi.mock("react", () => ({
  useCallback: (fn) => fn,
  useRef: (value) => ({ current: value }),
  useState: (initial) => [initial, setStateMock],
}));

vi.mock("../services/researchApi.js", () => ({
  buildApiUrl: (path) => `http://localhost:8000${path}`,
}));

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
