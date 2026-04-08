import { describe, expect, it } from "vitest";

import {
  buildStandaloneTracePath,
  buildTraceabilityParams,
  buildWorkspaceTracePath,
  describeTraceabilityState,
  mergeTraceabilityParams,
  readTraceabilityState,
} from "./traceabilityState.js";

describe("traceabilityState", () => {
  it("reads traceability fields from search params", () => {
    const params = new URLSearchParams(
      "work_id=w1&tab=graph&node=n1&chunk_fingerprint=fp1&section=intro&citation=2",
    );
    expect(readTraceabilityState(params)).toEqual({
      workId: "w1",
      tab: "graph",
      nodeId: "n1",
      chunkFingerprint: "fp1",
      section: "intro",
      citation: "2",
      askSession: "",
    });
  });

  it("reads ask_session and merge preserves it when updating tab", () => {
    const params = new URLSearchParams("work_id=w1&tab=graph&ask_session=s_abc");
    expect(readTraceabilityState(params).askSession).toBe("s_abc");
    const merged = mergeTraceabilityParams(params, { tab: "ask" });
    expect(merged.get("ask_session")).toBe("s_abc");
    expect(merged.get("tab")).toBe("ask");
  });

  it("builds workspace trace path with extras", () => {
    expect(
      buildWorkspaceTracePath("w1", "reader", {
        chunkFingerprint: "fp1",
        section: "intro",
        citation: "1",
      }),
    ).toBe("/workspace?work_id=w1&tab=reader&chunk_fingerprint=fp1&section=intro&citation=1");
  });

  it("builds standalone trace path without tab and merges updates", () => {
    expect(buildStandaloneTracePath("/reader", "w1", { chunkFingerprint: "fp1" })).toBe(
      "/reader?work_id=w1&chunk_fingerprint=fp1",
    );
    const merged = mergeTraceabilityParams(
      new URLSearchParams("work_id=w1&tab=graph&node=n1"),
      { nodeId: "n2", citation: "3" },
    );
    expect(merged.toString()).toBe("work_id=w1&tab=graph&node=n2&citation=3");
  });

  it("describes focus context for UI banners", () => {
    expect(
      describeTraceabilityState({
        citation: "2",
        chunkFingerprint: "fp1",
        section: "intro",
        nodeId: "n1",
      }),
    ).toEqual(["citation #2", "chunk fp1", "section intro", "node n1"]);
    expect(buildTraceabilityParams({ workId: "w1", tab: "ask" }).toString()).toBe("work_id=w1&tab=ask");
  });
});
