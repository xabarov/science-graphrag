/** @vitest-environment jsdom */
import { describe, expect, it, beforeEach } from "vitest";

import {
  buildInflightChatHref,
  clearInflightRunSnapshot,
  inflightMatchesSession,
  patchInflightRunSnapshot,
  readInflightRunSnapshot,
} from "./askRunPersistence.js";

describe("askRunPersistence", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    clearInflightRunSnapshot();
  });

  it("stores and reads in-flight snapshot", () => {
    patchInflightRunSnapshot({
      runId: "run-1",
      scopeKey: "standalone-ws:ws-1",
      sessionId: "sess-1",
      status: "running",
      lastSeq: 3,
      streamEvents: [{ type: "product_step" }],
    });
    const snap = readInflightRunSnapshot();
    expect(snap?.runId).toBe("run-1");
    expect(inflightMatchesSession("standalone-ws:ws-1", "sess-1")).toBe(true);
    expect(inflightMatchesSession("standalone-ws:ws-1", "other")).toBe(false);
  });

  it("buildInflightChatHref returns chat link for matching workspace", () => {
    patchInflightRunSnapshot({
      runId: "run-2",
      scopeKey: "standalone-ws:ws-9",
      sessionId: "sess-9",
      workspaceId: "ws-9",
      workId: "w-1",
      status: "running",
      lastSeq: 0,
      streamEvents: [],
      agentToolTrace: [],
    });
    expect(buildInflightChatHref("ws-9")).toBe("/chat?workspace_id=ws-9&ask_session=sess-9&work_id=w-1");
    expect(buildInflightChatHref("ws-other")).toBe("");
  });
});
