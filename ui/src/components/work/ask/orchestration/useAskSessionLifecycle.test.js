/** @vitest-environment jsdom */
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const listAskSessionsRequest = vi.hoisted(() =>
  vi.fn(async () => ({ data: { sessions: [], active_session_id: null } })),
);

vi.mock("../../../../services/researchApi.js", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    listAskSessions: (...args) => listAskSessionsRequest(...args),
  };
});

import { useAskSessionLifecycle } from "./useAskSessionLifecycle.js";

function stubLocalStorage() {
  const store = {};
  vi.stubGlobal("window", {
    localStorage: {
      getItem: (key) => (key in store ? store[key] : null),
      setItem: (key, value) => {
        store[key] = String(value);
      },
      removeItem: (key) => {
        delete store[key];
      },
      clear: () => {
        Object.keys(store).forEach((k) => {
          delete store[k];
        });
      },
    },
  });
}

describe("useAskSessionLifecycle", () => {
  let composerSuppressHydrateTurnIdRef;

  beforeEach(() => {
    listAskSessionsRequest.mockClear();
    composerSuppressHydrateTurnIdRef = { current: "" };
    stubLocalStorage();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  const noop = () => {};

  it("does not call listAskSessions when serverSync is false", () => {
    renderHook(() =>
      useAskSessionLifecycle({
        scopeKey: "standalone-ws:ws-1",
        locked: false,
        scopedWorkId: null,
        workspaceId: "ws-1",
        initialWorkId: "",
        urlSessionId: "",
        onUrlSessionIdChange: undefined,
        serverSync: false,
        sessionTick: 0,
        bumpSessions: noop,
        activeSessionId: null,
        setError: noop,
        setHistory: noop,
        setQuery: noop,
        setWorkId: noop,
        composerSuppressHydrateTurnIdRef,
      }),
    );
    expect(listAskSessionsRequest).not.toHaveBeenCalled();
  });

  it("pulls server session list when serverSync is true", async () => {
    renderHook(() =>
      useAskSessionLifecycle({
        scopeKey: "standalone-ws:ws-9",
        locked: false,
        scopedWorkId: null,
        workspaceId: "ws-9",
        initialWorkId: "",
        urlSessionId: "",
        onUrlSessionIdChange: undefined,
        serverSync: true,
        sessionTick: 0,
        bumpSessions: noop,
        activeSessionId: null,
        setError: noop,
        setHistory: noop,
        setQuery: noop,
        setWorkId: noop,
        composerSuppressHydrateTurnIdRef,
      }),
    );

    await act(async () => {
      await new Promise((r) => setTimeout(r, 0));
    });
    expect(listAskSessionsRequest).toHaveBeenCalledWith("standalone-ws:ws-9");
  });

  it("calls setError when listAskSessions fails under serverSync", async () => {
    const setError = vi.fn();
    listAskSessionsRequest.mockRejectedValueOnce(new Error("list failed"));
    renderHook(() =>
      useAskSessionLifecycle({
        scopeKey: "standalone-ws:ws-err",
        locked: false,
        scopedWorkId: null,
        workspaceId: "ws-err",
        initialWorkId: "",
        urlSessionId: "",
        onUrlSessionIdChange: undefined,
        serverSync: true,
        sessionTick: 0,
        bumpSessions: noop,
        activeSessionId: null,
        setError,
        setHistory: noop,
        setQuery: noop,
        setWorkId: noop,
        composerSuppressHydrateTurnIdRef,
      }),
    );

    await act(async () => {
      await new Promise((r) => setTimeout(r, 0));
    });
    expect(setError).toHaveBeenCalledWith("list failed");
  });
});
