/** @vitest-environment jsdom */
import { describe, expect, it, beforeEach } from "vitest";

import { patchInflightRunSnapshot } from "../work/ask/session/askRunPersistence.js";
import {
  LAST_CHAT_HREF_STORAGE_KEY,
  buildShellToolHref,
  locationHasPreservableTrace,
  persistLastChatHref,
  readLastChatHref,
  resolveDrawerChatHref,
} from "./shellNavHref.js";
import { CHAT_PATH, GRAPH_PATH } from "../../routes/paths.js";

describe("shellNavHref", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
  });

  it("buildShellToolHref preserves ask_session from current location", () => {
    const href = buildShellToolHref(CHAT_PATH, {
      locationSearch: "?ask_session=sess-1&workspace_id=ws-1",
      workspaceId: "ws-1",
    });
    expect(href).toContain("ask_session=sess-1");
    expect(href).toContain("workspace_id=ws-1");
  });

  it("buildShellToolHref preserves work_id and graph trace when switching tools", () => {
    const href = buildShellToolHref(CHAT_PATH, {
      locationSearch: "?workspace_id=ws-1&work_id=w-article&node=n1",
      workspaceId: "ws-1",
    });
    expect(href).toContain("work_id=w-article");
    expect(href).toContain("node=n1");
    expect(href).toContain("workspace_id=ws-1");
  });

  it("buildShellToolHref keeps workspace-wide graph scope without work_id", () => {
    const href = buildShellToolHref(GRAPH_PATH, {
      locationSearch: "?workspace_id=ws-1&node=n1",
      workspaceId: "ws-1",
    });
    expect(href).toContain("workspace_id=ws-1");
    expect(href).not.toContain("work_id=");
  });

  it("resolveDrawerChatHref preserves trace from graph when opening chat", () => {
    const href = resolveDrawerChatHref({
      locationSearch: "?workspace_id=ws-1&work_id=w-article&node=n1",
      workspaceId: "ws-1",
    });
    expect(href).toContain("work_id=w-article");
    expect(href).toContain("node=n1");
  });

  it("resolveDrawerChatHref preserves workspace-wide scope from graph", () => {
    const href = resolveDrawerChatHref({
      locationSearch: "?workspace_id=ws-1&node=n1",
      workspaceId: "ws-1",
    });
    expect(href).toContain("workspace_id=ws-1");
    expect(href).not.toContain("work_id=");
  });

  it("resolveDrawerChatHref prefers running inflight chat for workspace", () => {
    patchInflightRunSnapshot({
      runId: "run-live",
      scopeKey: "standalone-ws:ws-1",
      sessionId: "sess-inflight",
      workspaceId: "ws-1",
      status: "running",
      pendingUserQuery: "q",
      lastSeq: 0,
      streamEvents: [],
      agentToolTrace: [],
    });
    const href = resolveDrawerChatHref({ locationSearch: "", workspaceId: "ws-1" });
    expect(href).toContain("ask_session=sess-inflight");
    expect(href).toContain("workspace_id=ws-1");
  });

  it("resolveDrawerChatHref falls back to persisted last chat href without current trace", () => {
    persistLastChatHref("/chat?workspace_id=ws-9&ask_session=sess-old");
    const href = resolveDrawerChatHref({ locationSearch: "", workspaceId: "ws-9" });
    expect(href).toBe("/chat?workspace_id=ws-9&ask_session=sess-old");
  });

  it("locationHasPreservableTrace is false for empty search", () => {
    expect(locationHasPreservableTrace("")).toBe(false);
  });

  it("locationHasPreservableTrace ignores workspace_id-only query", () => {
    expect(locationHasPreservableTrace("?workspace_id=ws-1")).toBe(false);
  });

  it("persistLastChatHref only stores chat paths", () => {
    persistLastChatHref("/graph?workspace_id=ws-1");
    expect(readLastChatHref()).toBe("");
    persistLastChatHref("/chat?ask_session=a");
    expect(window.sessionStorage.getItem(LAST_CHAT_HREF_STORAGE_KEY)).toContain("ask_session=a");
  });
});
