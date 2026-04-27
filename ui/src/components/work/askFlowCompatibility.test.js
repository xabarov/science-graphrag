import { describe, expect, it } from "vitest";

import { deriveAskScopeKey } from "./askSessionState.js";
import {
  buildStandaloneEvidencePath,
  buildStandaloneTracePath,
  buildWorkspaceTracePath,
  describeTraceabilityState,
} from "./traceabilityState.js";
import { buildQueryBody, normalizeQueryResponse } from "../../services/researchApi.js";

describe("askFlowCompatibility", () => {
  it("keeps standalone ask links free of workspace tab params", () => {
    expect(buildStandaloneTracePath("/chat", "w1")).toBe("/chat?work_id=w1");
    expect(buildStandaloneTracePath("/evidence", "w1", { chunkFingerprint: "fp-1", citation: "2" })).toBe(
      "/evidence?work_id=w1&chunk_fingerprint=fp-1&citation=2",
    );
    expect(buildStandaloneEvidencePath("w1", { chunkFingerprint: "fp-1", citation: "2" })).toBe(
      "/evidence?work_id=w1&chunk_fingerprint=fp-1&citation=2",
    );
  });

  it("keeps workspace ask links scoped to the active tab", () => {
    expect(buildWorkspaceTracePath("w1", "ask", { chunkFingerprint: "fp-1", section: "intro", citation: "2" })).toBe(
      "/workspace?work_id=w1&tab=ask&chunk_fingerprint=fp-1&section=intro&citation=2",
    );
  });

  it("describes traceability context in a user-facing order", () => {
    expect(
      describeTraceabilityState({
        citation: "2",
        chunkFingerprint: "fp-1",
        section: "intro",
        nodeId: "node-1",
      }),
    ).toEqual(["citation #2", "chunk fp-1", "section intro", "node node-1"]);
  });

  it("partitions ask sessions by standalone vs locked workspace scope", () => {
    expect(deriveAskScopeKey({ locked: false, scopedWorkId: "w1" })).toBe("standalone");
    expect(deriveAskScopeKey({ locked: true, scopedWorkId: "w1" })).toBe("workspace:w1");
    expect(deriveAskScopeKey({ locked: false, scopedWorkId: null, workspaceId: "ws-1" })).toBe("standalone-ws:ws-1");
  });

  it("preserves global ask semantics when work id is empty", () => {
    expect(buildQueryBody("  compare detectors  ", "", 9)).toEqual({
      query: "compare detectors",
      work_id: null,
      workspace_id: null,
      top_k: 9,
      mode: "vector",
    });
    const normalized = normalizeQueryResponse({
      answer: "summary",
      citations: [],
      graph_context: { degraded: ["semantic_layer_disabled"] },
      retrieval_trace: { degraded: ["no_retrieval_hits"] },
    });
    expect(normalized.citations).toEqual([]);
    expect(normalized.retrieval_trace.degraded).toContain("no_retrieval_hits");
  });
});
