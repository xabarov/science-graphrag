/** @vitest-environment jsdom */
import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { readInflightRunSnapshot } from "../session/askRunPersistence.js";
import { readAskSessionUi } from "../session/askSessionState.js";
import { useAskPerformAgentSubmit } from "./useAskPerformAgentSubmit.js";

describe("useAskPerformAgentSubmit", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  it("creates and uses a stable session id before the first submit", async () => {
    const scopeKey = "standalone-ws:ws-first-submit";
    let resolveSubmit;
    const submit = vi.fn(
      () =>
        new Promise((resolve) => {
          resolveSubmit = () =>
            resolve({
              normalized: { answer: "ok", citations: [] },
              streamEvents: [],
              agentToolTrace: [],
            });
        }),
    );
    const onUrlSessionIdChange = vi.fn();
    const bumpSessions = vi.fn();

    const { result } = renderHook(() =>
      useAskPerformAgentSubmit({
        submit,
        webResearchEnabled: false,
        agentMode: "agent",
        workId: "",
        activeSessionId: null,
        locked: false,
        inWorkspace: false,
        corpusWorkspaceOnly: true,
        workspaceId: "ws-first-submit",
        bumpSessions,
        serverSync: false,
        t: (k) => k,
        scopeKeyRef: { current: scopeKey },
        streamFailureRef: { current: "" },
        composerSuppressHydrateTurnIdRef: { current: "" },
        setStreamingTarget: vi.fn(),
        setPendingUserQuery: vi.fn(),
        setQuery: vi.fn(),
        setError: vi.fn(),
        setNormalized: vi.fn(),
        setHistory: vi.fn(),
        onUrlSessionIdChange,
        inflightRunIdRef: { current: "" },
        inflightLastSeqRef: { current: 0 },
      }),
    );

    let pending;
    await act(async () => {
      pending = result.current("hello");
      await Promise.resolve();
    });

    const { activeId } = readAskSessionUi(scopeKey);
    expect(activeId).toBeTruthy();
    expect(onUrlSessionIdChange).toHaveBeenCalledWith(activeId);
    expect(bumpSessions).toHaveBeenCalled();
    expect(submit).toHaveBeenCalledWith(expect.objectContaining({ threadId: activeId }));
    expect(readInflightRunSnapshot()?.sessionId).toBe(activeId);

    await act(async () => {
      resolveSubmit();
      await pending;
    });
  });
});
