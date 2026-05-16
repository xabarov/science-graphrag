/** @vitest-environment jsdom */
import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  clearInflightRunSnapshot,
  patchInflightRunSnapshot,
} from "../session/askRunPersistence.js";
import { useAskInflightResume } from "./useAskInflightResume.js";

describe("useAskInflightResume", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    clearInflightRunSnapshot();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("restores pending UI and resumes when snapshot matches active session", async () => {
    const scopeKey = "standalone-ws:ws-resume";
    const sessionId = "sess-resume-1";

    patchInflightRunSnapshot({
      runId: "run-abc",
      scopeKey,
      sessionId,
      workspaceId: "ws-resume",
      pendingUserQuery: "hello from snapshot",
      lastSeq: 2,
      streamEvents: [{ type: "product_step", code: "searching_literature" }],
      agentToolTrace: [],
      status: "running",
    });

    const setPendingUserQuery = vi.fn();
    const setStreamingTarget = vi.fn();
    const setStreamEvents = vi.fn();
    const resumeStream = vi.fn(async () => ({
      normalized: { answer: "done", citations: [] },
      streamEvents: [],
      agentToolTrace: [],
    }));

    renderHook(() =>
      useAskInflightResume({
        scopeKey,
        activeSessionId: sessionId,
        onUrlSessionIdChange: vi.fn(),
        workspaceId: "ws-resume",
        locked: false,
        inWorkspace: false,
        corpusWorkspaceOnly: true,
        workId: "",
        serverSync: false,
        scopeKeyRef: { current: scopeKey },
        streamFailureRef: { current: "" },
        composerSuppressHydrateTurnIdRef: { current: "" },
        resumeStream,
        streamEventsCaptureRef: { current: [] },
        toolTraceCaptureRef: { current: [] },
        lastStreamNormalizedRef: { current: null },
        setStreamEvents,
        setAgentToolTrace: vi.fn(),
        setPendingUserQuery,
        setStreamingTarget,
        setQuery: vi.fn(),
        setHistory: vi.fn(),
        setNormalized: vi.fn(),
        setError: vi.fn(),
        bumpSessions: vi.fn(),
        setResumeUiStatus: vi.fn(),
        t: (k) => k,
      }),
    );

    await act(async () => {
      await waitFor(() => {
        expect(setPendingUserQuery).toHaveBeenCalledWith("hello from snapshot");
        expect(setStreamingTarget).toHaveBeenCalledWith({ scopeKey, sessionId });
        expect(setStreamEvents).toHaveBeenCalled();
        expect(resumeStream).toHaveBeenCalledWith({ runId: "run-abc", afterSeq: 2 });
      });
    });
  });

  it("keeps pending UI when resume returns without final answer", async () => {
    const scopeKey = "standalone-ws:ws-resume";
    const sessionId = "sess-resume-empty";
    patchInflightRunSnapshot({
      runId: "run-empty",
      scopeKey,
      sessionId,
      workspaceId: "ws-resume",
      pendingUserQuery: "still running",
      lastSeq: 4,
      streamEvents: [],
      agentToolTrace: [],
      status: "running",
    });

    const setPendingUserQuery = vi.fn();
    const setStreamingTarget = vi.fn();
    const setError = vi.fn();
    const resumeStream = vi.fn(async () => ({
      normalized: null,
      streamEvents: [],
      agentToolTrace: [],
    }));

    renderHook(() =>
      useAskInflightResume({
        scopeKey,
        activeSessionId: sessionId,
        onUrlSessionIdChange: vi.fn(),
        workspaceId: "ws-resume",
        locked: false,
        inWorkspace: false,
        corpusWorkspaceOnly: true,
        workId: "",
        serverSync: false,
        scopeKeyRef: { current: scopeKey },
        streamFailureRef: { current: "" },
        composerSuppressHydrateTurnIdRef: { current: "" },
        resumeStream,
        streamEventsCaptureRef: { current: [] },
        toolTraceCaptureRef: { current: [] },
        lastStreamNormalizedRef: { current: null },
        setStreamEvents: vi.fn(),
        setAgentToolTrace: vi.fn(),
        setPendingUserQuery,
        setStreamingTarget,
        setQuery: vi.fn(),
        setHistory: vi.fn(),
        setNormalized: vi.fn(),
        setError,
        bumpSessions: vi.fn(),
        setResumeUiStatus: vi.fn(),
        t: (k) => k,
      }),
    );

    await act(async () => {
      await waitFor(() => {
        expect(resumeStream).toHaveBeenCalled();
      });
    });
    expect(setPendingUserQuery).toHaveBeenCalledWith("still running");
    expect(setPendingUserQuery).not.toHaveBeenCalledWith("");
    expect(setStreamingTarget).toHaveBeenCalledWith({ scopeKey, sessionId });
    expect(setStreamingTarget).not.toHaveBeenCalledWith(null);
    expect(setError).not.toHaveBeenCalled();
  });

  it("does not call resume endpoint for local pending run id", async () => {
    const scopeKey = "standalone-ws:ws-resume";
    const sessionId = "sess-local-pending";
    patchInflightRunSnapshot({
      runId: "pending-sess-local-pending",
      scopeKey,
      sessionId,
      workspaceId: "ws-resume",
      pendingUserQuery: "waiting for run_started",
      lastSeq: 0,
      streamEvents: [],
      agentToolTrace: [],
      status: "running",
    });

    const resumeStream = vi.fn();
    const setPendingUserQuery = vi.fn();
    const setStreamingTarget = vi.fn();
    renderHook(() =>
      useAskInflightResume({
        scopeKey,
        activeSessionId: sessionId,
        onUrlSessionIdChange: vi.fn(),
        workspaceId: "ws-resume",
        locked: false,
        inWorkspace: false,
        corpusWorkspaceOnly: true,
        workId: "",
        serverSync: false,
        scopeKeyRef: { current: scopeKey },
        streamFailureRef: { current: "" },
        composerSuppressHydrateTurnIdRef: { current: "" },
        resumeStream,
        streamEventsCaptureRef: { current: [] },
        toolTraceCaptureRef: { current: [] },
        lastStreamNormalizedRef: { current: null },
        setStreamEvents: vi.fn(),
        setAgentToolTrace: vi.fn(),
        setPendingUserQuery,
        setStreamingTarget,
        setQuery: vi.fn(),
        setHistory: vi.fn(),
        setNormalized: vi.fn(),
        setError: vi.fn(),
        bumpSessions: vi.fn(),
        setResumeUiStatus: vi.fn(),
        t: (k) => k,
      }),
    );

    await act(async () => {
      await waitFor(() => {
        expect(setPendingUserQuery).toHaveBeenCalledWith("waiting for run_started");
      });
    });
    expect(setStreamingTarget).toHaveBeenCalledWith({ scopeKey, sessionId });
    expect(resumeStream).not.toHaveBeenCalled();
  });
});
