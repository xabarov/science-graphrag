/**
 * @vitest-environment jsdom
 */
import { describe, expect, it } from "vitest";

import { CHAT_PATH, EVIDENCE_PATH, GRAPH_PATH, READER_PATH, WORKSPACE_PATH } from "../../../routes/paths.js";
import {
  buildStandaloneEvidencePath,
  buildStandaloneTracePath,
  buildTraceabilityParams,
  buildWorkspaceTracePath,
  describeTraceabilityState,
  legacyWorkspaceTabRedirectTarget,
  mergeTraceabilityParams,
  readTraceabilityState,
} from "./traceabilityState.js";

describe("traceabilityState", () => {
  describe("legacy workspace tab in query", () => {
    it("reads traceability fields from search params", () => {
      const params = new URLSearchParams(
        "work_id=w1&tab=graph&node=n1&chunk_fingerprint=fp1&section=intro&citation=2",
      );
      expect(readTraceabilityState(params)).toEqual({
        workId: "w1",
        workspaceId: "",
        tab: "graph",
        nodeId: "n1",
        edgeId: "",
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

    it("mergeTraceabilityParams keeps tab when merging workspace-style params", () => {
      const merged = mergeTraceabilityParams(
        new URLSearchParams("work_id=w1&tab=graph&node=n1"),
        { nodeId: "n2", citation: "3" },
      );
      expect(merged.toString()).toBe("work_id=w1&tab=graph&node=n2&citation=3");
    });

    it("buildWorkspaceTracePath remains for deprecated workspace+tab URLs", () => {
      expect(
        buildWorkspaceTracePath("w1", "reader", {
          chunkFingerprint: "fp1",
          section: "intro",
          citation: "1",
        }),
      ).toBe(`${WORKSPACE_PATH}?work_id=w1&tab=reader&chunk_fingerprint=fp1&section=intro&citation=1`);
    });
  });

  describe("legacyWorkspaceTabRedirectTarget", () => {
    it("returns null when tab is absent or overview", () => {
      expect(legacyWorkspaceTabRedirectTarget(new URLSearchParams("work_id=w1"))).toBeNull();
      expect(legacyWorkspaceTabRedirectTarget(new URLSearchParams("work_id=w1&tab=overview"))).toBeNull();
    });

    it("maps tab=graph to standalone graph path with trace params", () => {
      expect(
        legacyWorkspaceTabRedirectTarget(
          new URLSearchParams("work_id=w1&tab=graph&node=n1&workspace_id=ws-1"),
        ),
      ).toBe(`${GRAPH_PATH}?work_id=w1&workspace_id=ws-1&node=n1`);
    });

    it("maps tab=reader to standalone reader path", () => {
      expect(
        legacyWorkspaceTabRedirectTarget(
          new URLSearchParams("work_id=w1&tab=reader&chunk_fingerprint=fp&section=s1"),
        ),
      ).toBe(`${READER_PATH}?work_id=w1&chunk_fingerprint=fp&section=s1`);
    });

    it("maps tab=ask to standalone chat path", () => {
      expect(
        legacyWorkspaceTabRedirectTarget(
          new URLSearchParams("work_id=w1&tab=ask&chunk_fingerprint=fp-1&section=intro&citation=2"),
        ),
      ).toBe(`${CHAT_PATH}?work_id=w1&chunk_fingerprint=fp-1&section=intro&citation=2`);
    });
  });

  it("reads edge id from query string", () => {
    const params = new URLSearchParams("work_id=w1&edge=edge-0&node=n1");
    expect(readTraceabilityState(params).edgeId).toBe("edge-0");
  });

  it("builds standalone trace path without tab and merges updates", () => {
    expect(buildStandaloneTracePath(READER_PATH, "w1", { chunkFingerprint: "fp1" })).toBe(
      "/reader?work_id=w1&chunk_fingerprint=fp1",
    );
    expect(buildStandaloneEvidencePath("w1", { workspaceId: "ws-9", chunkFingerprint: "fp1" })).toBe(
      `${EVIDENCE_PATH}?work_id=w1&workspace_id=ws-9&chunk_fingerprint=fp1`,
    );
  });

  it("mergeTraceabilityParams for standalone graph omits tab when includeTab is false", () => {
    const merged = mergeTraceabilityParams(
      new URLSearchParams("work_id=w1&node=n0"),
      { nodeId: "n1", edgeId: "" },
      { includeTab: false },
    );
    expect(merged.get("tab")).toBeNull();
    expect(merged.get("work_id")).toBe("w1");
    expect(merged.get("node")).toBe("n1");
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
    expect(
      describeTraceabilityState({
        edgeId: "e1",
        nodeId: "n1",
      }),
    ).toEqual(["edge e1", "node n1"]);
    expect(buildTraceabilityParams({ workId: "w1", tab: "ask" }).toString()).toBe("work_id=w1&tab=ask");
  });
});
