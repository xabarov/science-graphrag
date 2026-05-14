import { describe, expect, it, vi } from "vitest";

import {
  ASK_TURN_STREAM_EVENTS_CAP,
  buildAskFailureNormalizedStub,
  buildAskSessionTurnRecord,
  buildAskTurnDetailsFromNormalized,
  maybeRenameFirstAskSessionTurn,
  persistAskAgentTurnLocal,
} from "./askAgentTurnPersistence.js";

describe("buildAskTurnDetailsFromNormalized", () => {
  it("caps persisted stream_events", () => {
    const events = Array.from({ length: ASK_TURN_STREAM_EVENTS_CAP + 12 }, (_, i) => ({ type: "e", i }));
    const d = buildAskTurnDetailsFromNormalized(
      {
        answer: "a",
        citations: [],
        graph_context: {},
        retrieval_trace: {},
        warnings: [],
      },
      events,
      [{ t: 1 }],
    );
    expect(d.stream_events).toHaveLength(ASK_TURN_STREAM_EVENTS_CAP);
    expect(d.agent_tool_trace).toEqual([{ t: 1 }]);
  });
});

describe("buildAskFailureNormalizedStub", () => {
  it("returns an object with answer and empty citations", () => {
    const n = buildAskFailureNormalizedStub("err");
    expect(n.answer).toBe("err");
    expect(Array.isArray(n.citations)).toBe(true);
    expect(n.citations).toHaveLength(0);
  });
});

describe("buildAskSessionTurnRecord", () => {
  it("maps fields", () => {
    const turn = buildAskSessionTurnRecord({
      query: "q",
      turnWorkId: "w1",
      topK: 5,
      queryMode: "global",
      answerText: "a",
      citationCount: 2,
      details: { answer: "a" },
    });
    expect(turn).toMatchObject({
      query: "q",
      workId: "w1",
      topK: 5,
      mode: "global",
      answer: "a",
      citationCount: 2,
    });
  });
});

describe("persistAskAgentTurnLocal", () => {
  it("appends to active session when submitSid is empty", () => {
    const rememberAskHistory = vi.fn();
    const appendAskSessionTurn = vi.fn();
    const appendAskSessionTurnToSession = vi.fn();
    const readAskSessionUi = vi.fn(() => ({ activeId: "s1" }));
    const getAskSessionEntries = vi.fn();
    const getActiveSessionEntries = vi.fn(() => [{ id: "t1" }]);
    const scopeKeyRef = { current: "sk" };
    const turn = { query: "q" };
    const r = persistAskAgentTurnLocal({
      sk: "sk",
      submitSid: "",
      turn,
      rememberAskHistory,
      appendAskSessionTurn,
      appendAskSessionTurnToSession,
      readAskSessionUi,
      getAskSessionEntries,
      getActiveSessionEntries,
      scopeKeyRef,
    });
    expect(rememberAskHistory).toHaveBeenCalledWith(turn);
    expect(appendAskSessionTurn).toHaveBeenCalledWith("sk", turn);
    expect(appendAskSessionTurnToSession).not.toHaveBeenCalled();
    expect(r.composerTurnId).toBe("t1");
  });
});

describe("maybeRenameFirstAskSessionTurn", () => {
  it("renames only when first turn", () => {
    const renameAskSession = vi.fn();
    const t = maybeRenameFirstAskSessionTurn({
      sk: "sk",
      submitSid: "sid",
      q: "hello",
      entriesAfterLength: 1,
      renameAskSession,
    });
    expect(t).toBe("hello");
    expect(renameAskSession).toHaveBeenCalledWith("sk", "sid", "hello");
  });

  it("no-op when not first turn", () => {
    const renameAskSession = vi.fn();
    const t = maybeRenameFirstAskSessionTurn({
      sk: "sk",
      submitSid: "sid",
      q: "hello",
      entriesAfterLength: 2,
      renameAskSession,
    });
    expect(t).toBeNull();
    expect(renameAskSession).not.toHaveBeenCalled();
  });
});
