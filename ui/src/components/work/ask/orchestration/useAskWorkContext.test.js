/** @vitest-environment jsdom */
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const getWorkspace = vi.hoisted(() => vi.fn());
const getWorkDetail = vi.hoisted(() => vi.fn());
const getWorks = vi.hoisted(() => vi.fn());

vi.mock("../../../../utils/workspaceStore.js", () => ({
  getWorkspace: (...args) => getWorkspace(...args),
}));

vi.mock("../../../../services/researchApi.js", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    getWorkDetail: (...args) => getWorkDetail(...args),
    getWorks: (...args) => getWorks(...args),
  };
});

vi.mock("../../../../pages/WorkspacePage/utils/workContext.js", () => ({
  persistWorkId: vi.fn(),
}));

import { useAskWorkContext } from "./useAskWorkContext.js";

describe("useAskWorkContext", () => {
  beforeEach(() => {
    getWorkspace.mockReset();
    getWorkDetail.mockReset();
    getWorks.mockReset();
    getWorkspace.mockResolvedValue({ work_ids: ["w-alpha"] });
    getWorkDetail.mockImplementation(async (wid) => ({
      data: { work_id: wid, title: wid === "w-alpha" ? "Alpha Neutrino Study" : "", doi: "10.0/alpha" },
    }));
    getWorks.mockResolvedValue({ data: { items: [{ work_id: "g1", title: "Global hit" }] } });
  });

  it("loads workspace work list and filters client-side in searchWorks", async () => {
    const setWorkId = vi.fn();
    const { result } = renderHook(() =>
      useAskWorkContext({
        workspaceId: "ws-1",
        locked: false,
        workId: "",
        setWorkId,
      }),
    );

    await waitFor(() => {
      expect(result.current.workspaceSearchOptions.length).toBeGreaterThan(0);
    });

    const all = await result.current.searchWorks("");
    expect(all).toHaveLength(1);
    expect(all[0].work_id).toBe("w-alpha");

    const filtered = await result.current.searchWorks("neutrino");
    expect(filtered).toHaveLength(1);

    const miss = await result.current.searchWorks("zzz");
    expect(miss).toHaveLength(0);
  });

  it("uses global getWorks when not in a workspace", async () => {
    const setWorkId = vi.fn();
    const { result } = renderHook(() =>
      useAskWorkContext({
        workspaceId: "",
        locked: false,
        workId: "",
        setWorkId,
      }),
    );

    const rows = await result.current.searchWorks("hit");
    expect(getWorks).toHaveBeenCalled();
    expect(rows).toEqual([{ work_id: "g1", title: "Global hit" }]);
  });

  it("onArticlePicked sets work id and prefers rich row for chip without waiting on hydrate effect", async () => {
    const setWorkId = vi.fn();
    const { result } = renderHook(() =>
      useAskWorkContext({
        workspaceId: "ws-1",
        locked: false,
        workId: "",
        setWorkId,
      }),
    );

    await act(async () => {
      result.current.onArticlePicked({
        work_id: "w-beta",
        title: "Beta",
        doi: "10.0/beta",
      });
    });

    expect(setWorkId).toHaveBeenCalledWith("w-beta");
    expect(result.current.workDetailsForChip?.work_id).toBe("w-beta");
    expect(result.current.workDetailsForChip?.title).toBe("Beta");
  });

  it("clears workspace options when workspace has no work ids", async () => {
    getWorkspace.mockResolvedValueOnce({ work_ids: [] });
    const setWorkId = vi.fn();
    const { result } = renderHook(() =>
      useAskWorkContext({
        workspaceId: "ws-empty",
        locked: false,
        workId: "",
        setWorkId,
      }),
    );

    await waitFor(() => {
      expect(getWorkspace).toHaveBeenCalledWith("ws-empty");
    });
    expect(result.current.workspaceSearchOptions).toEqual([]);
  });

  it("does not load workspace works when locked", async () => {
    const setWorkId = vi.fn();
    const { result } = renderHook(() =>
      useAskWorkContext({
        workspaceId: "ws-locked",
        locked: true,
        workId: "w1",
        setWorkId,
      }),
    );

    await act(async () => {
      await new Promise((r) => setTimeout(r, 0));
    });
    expect(getWorkspace).not.toHaveBeenCalled();
    expect(result.current.workspaceSearchOptions).toEqual([]);
  });
});
